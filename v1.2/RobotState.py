import logging
import json, os
import time
import gevent
import IPC, threading
from collections import deque
from lib_helper import load_json_with_comments, func_name
from gevent.threadpool import ThreadPool

# 用于维护RobotState的工具库
# 注意：目前ipc操作时没有上锁，可能导致竞态

class RobotState:
    def __init__(self, STMLen=5):
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
        with self.lock: rs = { "Character": self.Character, "Volition": self.Volition, "STM": list(self.STM) }
        self.ipc.post_message(receiver="Public_RobotState", content=json.dumps(rs), sender=self.ipc.client_name)

    def setVolition(self, newVolition: list):
        """设置意志，有锁"""
        self.Volition = newVolition
        self.publish()

    def updateSTM(self, newMessage: dict): 
        """更新STM，带锁。"""
        with self.lock: self.STM.append(newMessage)

    # 协程

    def VolitionAndPostCoroutine(self, cooldown=1):
        while True:
            dic = self.ipc.query_latest_message(receiver="RobotState_Volition")
            if not dic["messages"]: continue
            dic = json.loads(dic["messages"][0]["content"])
            self.setVolition(dic) # 不是dict，是列表，只是变量名懒得改了
            gevent.sleep(cooldown)

    # 线程

    def STMUpdateThread(self):
        """阻塞监听新的短期记忆"""
        while True:
            time.sleep(1)
            messagelist = []
            while True:
                message = self.ipc.fetch_earliest_messages(receiver="RobotState_STM")
                if not message["messages"]: break
                else: messagelist.append(json.loads(message["messages"][0]["content"]))
            if not messagelist: continue
            for i in messagelist: self.updateSTM(i)
            self.publish()

    # 启动

    def run(self) -> None:
        pool = ThreadPool(1)
        pool.spawn(self.VolitionAndPostCoroutine)
        threading.Thread(target=self.STMUpdateThread, daemon=True).start()
        while True: gevent.sleep(600)
