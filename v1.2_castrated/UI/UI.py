import logging
import os, sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import func_name
import Processors.LLMAPI
import UI.subtitle as subtitle
import threading, UI.TTS, queue, UI.Sensor_api.sensor_api

WAIT = 2

class Desire:
    """一个欲望实在的初步实现，检测键盘是否被按下"""

    def __init__(self, dist=400, dwell=1, debug=False): 
        self.debug = debug
        self.sensor = UI.Sensor_api.sensor_api.ProximitySensor()
        self.dist = dist
        self.dwell = dwell
        self.sitting = False
        threading.Thread(target=self.MainThread, daemon=True).start()

    # 线程
    
    def MainThread(self): 
        """定期发送状态，以防当前状态被冲走"""
        while True:
            self.sensor.update()
            if self.sensor.distance <= self.dist:
                logging.debug(f"{func_name()}: Sensor Positive Feedback")
                self.sitting = True
            else:
                logging.debug(f"{func_name()}: Sensor Negative Feedback")
                self.sitting = False
            time.sleep(self.dwell)

class DesireSim:
    """训练时使用的周期性简化版欲望实在"""

    def __init__(self): 
        self.sitting = False
        import UI.Trigger
        self.trigger = UI.Trigger.TriggerManager(self)

    def Trigger(self): self.sitting = True

    def UnTrigger(self): self.sitting = False

class Output:
    def __init__(self): 
        self.llm = Processors.LLMAPI.LLM()
        self.SpeakQueue = queue.Queue(maxsize=10) # {"en": , "zh": }
        self.tts = UI.TTS.TTS_app()
        self.subtitle = subtitle.ThreadSafeSubtitle()
        self.window = self.subtitle.create_window("_")
        self.window.show()
        threading.Thread(target=self.SpeakQueueThread, daemon=True).start()
    
    def quit(self): self.window.exit()

    # 线程

    def SpeakQueueThread(self, cooldown=0.2):
        """用于说话的处理队列"""
        while True:
            content = self.SpeakQueue.get()
            logging.info(f"{func_name()}: Speaking: {content}")
            th = threading.Thread(target=self.tts.Speak, args=(content.get("en", ""),), daemon=True)
            th.start()
            time.sleep(WAIT)
            text = content.get("zh", "_")+"\n"+content.get("en", "_")
            self.subtitle.update_text(text)
            th.join()
            time.sleep(cooldown)
            # self.subtitle.update_text("_")

if __name__ == "__main__": 
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    