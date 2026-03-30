import logging
import os, sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import func_name
import Processors.LLMAPI
import IPC, threading, gevent, UI.TTS, queue, UI.Sensor_api.sensor_api

class Desire:
    """一个欲望实在的初步实现，检测键盘是否被按下，通过IPC更新。发信为1或-1"""

    def __init__(self, dist=400, dwell=3, debug=False): 
        self.debug = debug
        self.ipc = IPC.BulletinClient("UI_Desire")
        self.sensor = UI.Sensor_api.sensor_api.ProximitySensor()
        self.dist = dist
        self.dwell = dwell

    # 线程
    
    def MainThread(self): 
        """定期发送状态，以防当前状态被冲走"""
        while True:
            self.sensor.update()
            if self.debug: logging.debug(f"Dist: {self.sensor.distance} mm")
            if self.sensor.distance <= self.dist:
                logging.info(f"{func_name()}: Sensor Positive Feedback")
                if not self.debug: self.ipc.post_message("Public_UI_Desire", str(1), self.ipc.client_name)
            else:
                logging.info(f"{func_name()}: Sensor Negative Feedback")
                if not self.debug: self.ipc.post_message("Public_UI_Desire", str(-1), self.ipc.client_name)
            time.sleep(self.dwell)

class DesireSim:
    """训练时使用的周期性简化版欲望实在"""

    def __init__(self): self.ipc = IPC.BulletinClient("UI_Desire")

    # 协程
    
    def MainThread(self): 
        while True:
            for i in range(6):
                self.ipc.post_message("Public_UI_Desire", str(1), self.ipc.client_name)
                time.sleep(10)
            for i in range(6):
                self.ipc.post_message("Public_UI_Desire", str(-1), self.ipc.client_name)
                time.sleep(10)


class Output:
    """一个初步的互动性Output，只实现了语音输出"""

    def __init__(self): 
        self.llm = Processors.LLMAPI.LLM()
        self.SpeakQueue = queue.Queue(maxsize=5)
        self.tts = UI.TTS.TTS_app()
    
    # 线程

    def SpeakQueueThread(self, cooldown=0.2):
        """用于说话的处理队列"""
        while True:
            content = self.SpeakQueue.get()
            logging.info(f"{func_name()}: Speaking: {content}")
            self.tts.Speak(content)
            time.sleep(cooldown)

    def TextGenerationThread(self, cooldown=5):
        """生成文本的线程"""
        while True:
            time.sleep(cooldown)
            ret = self.llm.Chat()
            if ret == {}: continue
            ret = ret.get("content", "").strip()
            if self.SpeakQueue.full(): 
                try: self.SpeakQueue.get(timeout=60)
                except: pass
            if ret: self.SpeakQueue.put(ret)


def main():
    d = Desire() # 在这里修改
    o = Output()
    threading.Thread(target=d.MainThread, daemon=True).start()
    threading.Thread(target=o.SpeakQueueThread, daemon=True).start()
    threading.Thread(target=o.TextGenerationThread, daemon=True).start()
    while True: time.sleep(1800)

if __name__ == "__main__": 
    d = Desire(True)
    threading.Thread(target=d.MainThread, daemon=True).start()
    input()