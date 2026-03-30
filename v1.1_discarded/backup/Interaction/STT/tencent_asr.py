import base64
import time
import numpy as np
import pyaudio
import threading
import queue
import os
import IPC
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.asr.v20190614 import asr_client, models
import logging

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

class LiveTranscriber:
    def __init__(self, settings, show=True):
        self.show = show
        # 腾讯云API配置
        self.tencent_secret_id = settings["id"]
        self.tencent_secret_key = settings["key"]
        self.region = settings["region"]
        self.service_type = settings["service_type"]
        
        # 初始化腾讯云客户端
        cred = credential.Credential(self.tencent_secret_id, self.tencent_secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = settings["endpoint"]
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        self.asr_client = asr_client.AsrClient(cred, self.region, client_profile)
        
        # 音频参数
        self.RATE = 16000
        self.CHUNK = 1024
        self.SILENCE_THRESHOLD = 1.5  # 静音判断阈值(秒)
        self.NOISE_SAMPLE_DURATION = 3  # 噪音采样时长(秒)
        
        # 音频缓冲区
        self.audio_buffer = np.array([], dtype=np.float32)
        self.noise_profile = None
        
        # 语音状态跟踪
        self.is_speaking = False
        self.last_voice_time = time.time()
        self.speech_start_time = 0
        
        # 结果队列
        self.text_queue = queue.Queue()
        
        # 控制标志
        self.running = False
        self.stream_id = None
        self.seq_id = 0  # 流式传输序列号

        self.ipc = IPC.BulletinClient("tencent-asr")

    def logger(self, message):
        if self.show: logging.info(f"tencent_asr.LiveTranscriber: {message}")

    def _collect_noise_sample(self):
        """采集环境噪音样本"""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        self.logger(f"正在采集{self.NOISE_SAMPLE_DURATION}秒环境噪音样本，请保持安静...")
        noise_frames = []
        
        for _ in range(0, int(self.RATE / self.CHUNK * self.NOISE_SAMPLE_DURATION)):
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            noise_frames.append(np.frombuffer(data, dtype=np.float32))
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        self.noise_profile = np.concatenate(noise_frames)
        self.logger("噪音样本采集完成")

    def _send_audio_stream(self, audio_data):
        """发送音频流到腾讯云"""
        try:
            # 1. 将float32音频归一化到[-1, 1]范围
            audio_data = audio_data / np.max(np.abs(audio_data)) if np.max(np.abs(audio_data)) > 0 else audio_data
            
            # 2. 转为16bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # 3. 转为Base64字符串
            audio_bytes = audio_int16.tobytes()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # 4. 构造流式请求
            req = models.SentenceRecognitionRequest()
            req.EngSerViceType = self.service_type
            req.SourceType = 1
            req.VoiceFormat = "pcm"
            req.Data = audio_base64
            req.DataLen = len(audio_bytes)
            req.UsrAudioKey = f"stream_{int(time.time())}_{self.seq_id}"
            self.seq_id += 1
            
            # 5. 发送音频流
            resp = self.asr_client.SentenceRecognition(req)
            if resp and resp.Result:
                return resp.Result
            return None
            
        except Exception as e:
            self.logger(f"流式API调用失败: {e}")
            self.ipc.post_message(receiver="STTServer", sender=self.ipc.client_name, 
                                content=f"Err: {e}")
            return None

    def start(self):
        """启动录音和转录线程"""
        self._collect_noise_sample()
        self.running = True
        self.ipc.post_message(receiver="STTServer", content="Done", sender=self.ipc.client_name)
        
        self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()
        
        self.transcribing_thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self.transcribing_thread.start()

    def stop(self):
        """停止所有线程"""
        self.running = False
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join()
        if hasattr(self, 'transcribing_thread'):
            self.transcribing_thread.join()

    def _record_audio(self):
        """从麦克风录制音频"""
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        self.logger("开始录音，请说话...")
        
        while self.running:
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            chunk = np.frombuffer(data, dtype=np.float32)
            
            # 语音活动检测
            if self._is_voice(chunk):
                self.last_voice_time = time.time()
                if not self.is_speaking:
                    self.is_speaking = True
                    self.speech_start_time = self.last_voice_time
                    self.logger("检测到语音开始")
            
            self.audio_buffer = np.append(self.audio_buffer, chunk)
        
        stream.stop_stream()
        stream.close()
        p.terminate()

    def _is_voice(self, audio_chunk):
        """语音检测"""
        rms = np.sqrt(np.mean(audio_chunk**2))
        noise_rms = np.sqrt(np.mean(self.noise_profile**2))
        return rms > max(0.02, noise_rms * 3)

    def _transcribe_loop(self):
        """转录主循环"""
        while self.running:
            current_time = time.time()
            
            if self.is_speaking and (current_time - self.last_voice_time) > self.SILENCE_THRESHOLD:
                self.is_speaking = False
                self.logger("检测到语音结束")
                
                if len(self.audio_buffer) > 0:
                    audio_to_process = self.audio_buffer.copy()
                    self.audio_buffer = np.array([], dtype=np.float32)
                    
                    # 发送音频流并获取结果
                    text = self._send_audio_stream(audio_to_process)
                    if text:
                        self.text_queue.put(text)
                        self.logger(f"识别结果: {text}")
                        self.ipc.post_message(receiver="STTServer", sender=self.ipc.client_name,
                                            content=f"Msg: {text}")
            
            time.sleep(0.1)

    def get_last_text(self):
        """获取最新识别结果"""
        try:
            return self.text_queue.get_nowait()
        except queue.Empty:
            return None

if __name__ == "__main__":
    transcriber = LiveTranscriber()
    
    try:
        transcriber.start()
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n停止录音...")
        transcriber.stop()