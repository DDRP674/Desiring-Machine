import json, os
import gevent
import IPC, threading
from collections import deque
from lib_helper import load_json_with_comments
from gevent.threadpool import ThreadPool

# 用于维护RobotState的工具库

class RobotState:
    def __init__(self, STMLen=10):
        settingspath = os.path.normpath("settings.json")
        self.settings = load_json_with_comments(settingspath)
        CharacterPath = os.path.normpath(self.settings["Character"])
        with open(CharacterPath, "r", encoding="utf-8") as f: self.Character = f.read()
        self.Scene = "" # 未启用
        self.Emotion = "" # 未启用
        self.Volition = [] # 这是一个列表，其中第一个是最子的意志，往后都是母意志
        self.STM = deque(maxlen=STMLen)
        self.ipc = IPC.BulletinClient("RobotState")
        self.lock = threading.Lock()

    def publish(self):
        """用于把当前机器人状态发布在IPC上，便于获取。这个函数应该在每次修改的时候被调用。带锁。
        \n格式：\n
        {"Character": "", "Volition": ["",""], "STM": [{},{}]}"""
        with self.lock:
            rs = { "Character": self.Character, "Volition": self.Volition, "STM": list(self.STM) }
            self.ipc.post_message(receiver="Public", content=json.dumps(rs), sender=self.ipc.client_name)

    def setVolition(self, newVolition: list):
        """设置意志，有锁"""
        with self.lock: self.Volition = newVolition
        self.publish()

    def updateSTM(self, newMessage: dict): 
        """更新STM，带锁。这个函数应该由UI模块调用"""
        with self.lock: self.STM.append(newMessage)
        self.publish()

    # 协程

    def VolitionCoroutine(self, cooldown=1):
        while True:
            with self.lock: dic = self.ipc.query_latest_message(sender="VolitionTree", receiver="RobotState")
            if not dic["messages"]: continue
            lis = json.loads(dic["messages"][0]["content"])
            self.setVolition([i["content"] for i in lis])
            gevent.sleep(cooldown)

    # 启动

    def run(self) -> None:
        pool = ThreadPool(3)
        pool.spawn(self.VolitionCoroutine)
        while True: gevent.sleep(600)
