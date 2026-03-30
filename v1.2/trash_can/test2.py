import threading
import time
import keyboard


class TriggerManager:
    """直接启动线程"""

    def __init__(self, char="k"):
        self.triggered = False
        keyboard.on_press_key(char, self.on_key_press)
        keyboard.on_release_key(char, self.on_key_release)
        threading.Thread(target=self.RunThread, daemon=True).start()

    def on_key_press(self, key) -> None:
        if self.triggered: return
        self.triggered = True
        print(f"检测到按下{key}")

    def on_key_release(self, key):
        time.sleep(1)
        self.triggered = False
        print(f"检测到放开{key}")

    # 线程

    def RunThread(self):
        print(f"键盘监听开始，按ESC退出")
        keyboard.wait('esc')
        keyboard.unhook_all()

t = TriggerManager()
threading.Thread(target=t.RunThread, daemon=True).start()
while True:
    time.sleep(1800)