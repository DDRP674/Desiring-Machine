import logging
import keyboard
import os, sys, threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import func_name

class TriggerManager:
    """直接启动线程"""

    def __init__(self, DesireObject, char="k"):
        self.DesireObject = DesireObject
        keyboard.on_press_key(char, self.on_key_press)
        keyboard.on_release_key(char, self.on_key_release)
        threading.Thread(target=self.RunThread, daemon=True).start()

    def on_key_press(self, key) -> None:
        if self.DesireObject.triggered: return
        logging.info(f"{func_name()}: 检测到按下{key}")
        self.DesireObject.Trigger()

    def on_key_release(self, key):
        logging.info(f"{func_name()}: 检测到放开{key}")
        self.DesireObject.UnTrigger()

    # 线程

    def RunThread(self):
        logging.info(f"{func_name()}: 键盘监听开始，按ESC退出")
        keyboard.wait('esc')
        keyboard.unhook_all()
