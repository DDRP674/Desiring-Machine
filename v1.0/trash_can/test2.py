import keyboard
import time

def on_key_press(key):
    print(f"按键 {key} 被按下 - 启动功能")

def on_key_release(key):
    print(f"按键 {key} 被释放 - 停止功能")

# 指定特定按键
keyboard.on_press_key('a', on_key_press)
keyboard.on_release_key('a', on_key_release)

print("按ESC退出")
keyboard.wait('esc')
keyboard.unhook_all()