import logging
import socket
import azure.cognitiveservices.speech as speechsdk
import sys, os
import threading
import numpy as np
import sounddevice as sd

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)
from lib_helper import load_json_with_comments

class AudioStreamCallback(speechsdk.audio.PushAudioOutputStreamCallback):
    def __init__(self, socket_client, logger, samplerate=16000):
        super().__init__()
        self.socket_client = socket_client
        self.logger = logger
        self.connected = True
        self.samplerate = samplerate
        self.stream = sd.OutputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype='int16',
            blocksize=0
        )
        self.stream.start()

    def write(self, buffer: memoryview) -> int:
        try:
            if self.connected:
                samples = np.frombuffer(buffer, dtype=np.int16)
                volume = (np.mean(samples**2)/1100)**2
                # 发送音量（float）到端口，转为字符串再编码
                volume_bytes = f"{volume:.2f}\n".encode("utf-8")
                self.socket_client.sendall(volume_bytes)
                # self.logger(f"发送实时音量: {volume:.2f}")
                self.stream.write(samples)  # 本地播放
                return buffer.nbytes
        except Exception as e:
            self.logger(f"Failed to send volume data or play audio: {str(e)}")
            self.connected = False
        return 0

    def close(self):
        try:
            if self.connected:
                self.socket_client.close()
        except Exception as e:
            self.logger(f"Failed to close socket: {str(e)}")
        self.stream.stop()
        self.stream.close()
        self.connected = False

class azure:
    def __init__(self, show=True):
        self.show = show
        self.settings = load_json_with_comments("settings.json")
        self.l2d_settings = self.settings["live2d"]
        self.settings = self.settings["tts"]["azure-tts-settings"]
        self.ssml = """
<speak version='1.0' 
        xmlns='http://www.w3.org/2001/10/synthesis' 
        xmlns:mstts="https://www.w3.org/2001/mstts"
        xml:lang="{lang}">
    <voice name="{voice_name}">
        <mstts:express-as style="{emotion}">
            <prosody rate='{speed}' pitch='{pitch}' volume='{volume}'>
                {text}
            </prosody>
        </mstts:express-as>
    </voice>
</speak>
"""
        self.parameters = {
            "lang": self.settings.get("language", "en-US"),
            "voice_name": self.settings.get("voice_name", "en-US-AshleyNeural"),
            "speed": self.settings.get("voice_speed", "medium"),
            "pitch": self.settings.get("voice_pitch", "+30Hz"),
            "volume": self.settings.get("voice_volume", "medium"),
            "emotion": "",
            "text": ""
        }
        self.emotion_map = self.settings["emotion_map"]
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.settings["api_key"], 
            region=self.settings["region"]
        )
        self.serve_live2d = self.settings["Serve_Live2d"]

        # Socket配置
        self.socket_host = "127.0.0.1"
        self.socket_port = self.l2d_settings["audio_port"]
        self.socket_connected = False
        self.socket_client = None
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
        )
        self.synthesis_lock = threading.Lock()

    def logger(self, message):
        if self.show: logging.info(f"azure_tts.azure: {message}")

    def connect_to_unity(self):
        """连接到Unity的Socket服务器"""
        for i in range(5):
            try:
                self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_client.connect((self.socket_host, self.socket_port))
                self.socket_connected = True
                self.logger("Successfully connected to Unity at {}:{}".format(self.socket_host, self.socket_port))
                return True
            except Exception as e:
                self.logger("Failed to connect to Unity: {}".format(str(e)))
                self.socket_connected = False
                if i == 4: break
                self.logger(f"尝试重连第{i+1}次")
        return False

    def speak(self, text_with_options):
        with self.synthesis_lock:
            l = text_with_options.split(" --with-emotion ")
            emotion = ""
            if len(l) > 1:
                text = l[0]
                emotion_description = l[1]
                for i, j in self.emotion_map.items():
                    if i in emotion_description:
                        emotion = j
                        break
            else:
                text = l[0]
            self.parameters["text"] = text
            self.parameters["emotion"] = emotion
            formatted_ssml = self.ssml.format(**self.parameters)

            if self.serve_live2d:
                # 发送音量数据到Unity并本地播放
                if not self.socket_connected:
                    if not self.connect_to_unity():
                        if self.socket_connected:
                            self.socket_client.close()
                            self.socket_connected = False
                        return None

                if self.socket_connected:
                    callback = AudioStreamCallback(self.socket_client, self.logger)
                    stream = speechsdk.audio.PushAudioOutputStream(callback)
                    audio_config = speechsdk.audio.AudioOutputConfig(stream=stream)
                    speech_synthesizer = speechsdk.SpeechSynthesizer(
                        speech_config=self.speech_config, 
                        audio_config=audio_config
                    )
                    result = speech_synthesizer.speak_ssml_async(formatted_ssml).get()
                    callback.close()
                    self.socket_connected = False  # <--- 关键：每次用完都设为False，下次自动重连
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        self.logger(f"RMS streamed to Unity and audio played for text [{text}]")
                        return "rms_streamed_to_unity"
                    else:
                        return None
            else:
                # 仅本地播放
                audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
                speech_synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=self.speech_config,
                    audio_config=audio_config
                )
                result = speech_synthesizer.speak_ssml_async(formatted_ssml).get()
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    self.logger("azure_tts.azure.speak: Speech synthesized and played for text [{}]".format(text))
                    return None
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation_details = result.cancellation_details
                    self.logger("azure_tts.azure.speak: Speech synthesis canceled: {}".format(cancellation_details.reason))
                    if cancellation_details.reason == speechsdk.CancellationReason.Error:
                        self.logger("azure_tts.azure.speak: Error details: {}".format(cancellation_details.error_details))
                    return None

if __name__ == "__main__":
    a = azure()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    import time
    a.speak("Where wonder paints the sky’s embrace.")
    a.speak("No chains of gray, just hues so free.")
    time.sleep(5)
    a.speak("Please take me away, take me to the world of anime.")
    time.sleep(10)