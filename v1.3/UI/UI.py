import logging
import os, sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Processors.LLMAPI
import IPC, threading, gevent, UI.TTS, queue, UI.Trigger
from gevent.threadpool import ThreadPool

class Desire:
    """一个欲望实在的初步实现，检测键盘是否被按下，通过IPC更新。发信为1或-1"""

    def __init__(self): 
        self.ipc = IPC.BulletinClient("UI_Desire")
        self.triggered = False
        self.trigger = UI.Trigger.TriggerManager(self, "k")

    def Trigger(self):
        self.triggered = True
        self.ipc.post_message("Public", str(1), self.ipc.client_name)

    def UnTrigger(self):
        self.triggered = False
        self.ipc.post_message("Public", str(-1), self.ipc.client_name)

    # 协程
    
    def SendCoroutine(self, cooldown=60): 
        """定期发送状态，以防当前状态被冲走"""
        while True:
            gevent.sleep(cooldown)
            if self.triggered: self.ipc.post_message("Public", str(1), self.ipc.client_name)
            else: self.ipc.post_message("Public", str(-1), self.ipc.client_name)


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
            logging.info(f"Speaking: {content}")
            self.tts.Speak(content)
            time.sleep(cooldown)

    def TextGenerationThread(self, cooldown=0.5):
        """生成文本的线程"""
        while True:
            time.sleep(cooldown)
            ret = self.llm.Chat()
            if ret == {}: continue
            ret = ret.get("content", "").strip()
            if self.SpeakQueue.full(): self.SpeakQueue.get()
            if ret: self.SpeakQueue.put(ret)


def main():
    d = Desire()
    o = Output()
    pool = ThreadPool(1)
    pool.spawn(d.SendCoroutine)
    threading.Thread(target=o.SpeakQueueThread, daemon=True).start()
    threading.Thread(target=o.TextGenerationThread, daemon=True).start()
    while True: time.sleep(1800)

if __name__ == "__main__": 
    main()