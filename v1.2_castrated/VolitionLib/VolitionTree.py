import collections
import logging
import json, sys, os
import time
import random, threading
import uuid
from anytree import RenderTree, Node
import numpy as np
import gevent
from gevent.threadpool import ThreadPool
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import func_name, load_json_with_comments, get_filename
import VolitionLib.VolitionNode as VolitionNode
import VolitionLib.initialNodes as initialNodes
from Processors.LLMAPI import LLM
import VolitionLib.Visualize.API as API
import UI.UI, Tools.Tools

# 没说上锁就是本函数内没锁，子函数里可能有

TEMPERATURE = 0.35

class CastratedVolitionTree:
    def __init__(self, debug=False):
        self.lock = threading.Lock()
        self.settings = load_json_with_comments(os.path.normpath("./settings.json"))
        self.do_display = self.settings["do_display"]

        self.llms = LLM()
        self.desire = UI.UI.DesireSim() if debug else UI.UI.Desire()
        self.output = UI.UI.Output()

        self.root = self.TreeConstructor(initialNodes.INITIAL_NODES)
        self.current = self.root

        self.state = 0 # 0: 无人, 1: 有人, 2: 将要离开
        self.i = 0
        self.manager = None
        self.last_choice = None
        self.past_choices = collections.deque(maxlen=3)

        logging.info("树初始化完毕")
        threading.Thread(target=self.run, args=(debug,), daemon=True).start()

    # 初始化建树函数

    def TreeConstructor(self, JsonData) -> Node|None:
        """根据Json文件构建一个树，递归"""
        if type(JsonData) == type(""): JsonData = json.loads(JsonData)
        if not JsonData: return None
        current = self.CreateNode(content=JsonData.get("content", ""), name=JsonData.get("id", ""))
        ChildrenList = JsonData.get("children", [])
        if not ChildrenList: return current
        for child in ChildrenList:
            if type(child) != type({}): continue
            subtree = self.TreeConstructor(child)
            if subtree != None: current.children += (subtree,) 
        return current
    
    def CreateNode(self, content: str, name=None) -> Node:
        """创建一个节点"""
        data = VolitionNode.VolitionData(content)
        if name == None: name = str(uuid.uuid4())
        return Node(name, data=data)

    # 当前节点变化函数

    def Choose(self, temperature=0.35) -> Node:
        """选一个节点。使用Softmax"""
        values = []
        for child in self.root.children: values.append(child.data.value)
        values = np.array(values)
        values = np.exp(values/temperature)
        return random.choices(self.root.children, values, k=1)[0]

    def Backward(self) -> bool:
        """退回，带锁"""
        with self.lock:
            if self.root.name == self.current.name:
                logging.info("Didnt Backward: At root")
                return False
            self.current = self.root
            logging.info("Backward Success")
            return True

    # 其他

    def Visualize(self) -> None:
        for pre, _, node in RenderTree(self.root): logging.info(f"{pre}{round(node.data.value, 3)}")
        for pre, _, node in RenderTree(self.root): logging.info(f"{pre}{node.data.content}")
        for pre, _, node in RenderTree(self.root): logging.info(f"{pre}{node.name}")

    # 协程

    def EvaluateCoroutine(self, cooldown=1, reward=0.01, decay=0.95) -> None: # 待优化
        """每cooldown时间当前节点加上reward再总体做平均。带锁"""
        while True:
            gevent.sleep(cooldown)
            cond = True
            with self.lock: 
                if self.current.name == self.root.name: cond = False
            if not cond: 
                with self.lock: self.i = 0
                continue
            with self.lock:
                self.current.data.value += reward*(decay**self.i)
                avr = 0
                for child in self.root.children: avr += child.data.value
                if avr != 0: 
                    for child in self.root.children: child.data.value /= avr
                self.i += 1

    def VisualizeCoroutine(self, cooldown=5) -> None:
        """显示树状态""" # 未启用
        while True:
            # with self.lock: self.Visualize()
            with self.lock: print([node.name for node in self.past_choices])
            gevent.sleep(cooldown)

    # 线程

    def DisplayThread(self, cooldown=0.5) -> None:
        """在前端展示树"""
        if not self.do_display: return
        try: JSAPI = API.API()
        except Exception as e:
            logging.warning(f"{func_name()}: 未启动前端：{e}")
            return
        while True:
            with self.lock: 
                TreeJsonData = VolitionNode.getNodeJsonVisualization(self.root)
                CurrentID = self.current.name if self.current else "Root"
            JSAPI.Update(TreeJsonData, CurrentID)
            time.sleep(cooldown)

    def StateMachine_0(self, cooldown=10) -> None: 
        """无人"""
        while True:
            while self.state != 0: time.sleep(0.1)
            # 执行attract
            logging.info(f"{func_name()}: 执行attract")
            tasknode = self.Choose(TEMPERATURE)
            d = self.llms.Attract(tasknode.data.content)
            self.output.SpeakQueue.put(d)
            with self.lock: self.last_choice = tasknode
            time.sleep(cooldown)

    def StateMachine_1(self, cooldown=0.5) -> None: 
        """有人，执行交易"""
        while True:
            time.sleep(cooldown)
            with self.lock:
                if self.state != 1: 
                    if self.manager != None:
                        if self.manager.running: self.manager.stop()
                        self.manager = None
                    continue
                if self.manager == None: 
                    self.manager = Tools.Tools.Managers.get(self.current.name, None)
                    logging.info(f"{func_name()}: Manager Registered: {self.current.data.content}")
                if self.manager != None and not self.manager.running: 
                    self.manager.do()
            cond = False
            with self.lock:
                if self.manager != None and self.manager.keep1 == {}: cond = True
            if cond: 
                keep1 = self.llms.Keep1(self.current.data.content) 
                with self.lock: self.manager.keep1 = keep1

    def StateMachine(self, wait=12) -> None: 
        """状态机，它将会检测self.sitting"""
        while True:
            # 如果无人，则每八秒attract一次
            # 如果有人，则执行交易
            # 如果即将离去，则执行keep
            time.sleep(0.1)
            if self.desire.sitting and self.state == 0: 
                logging.info("Sitting, State: 0 -> 1")
                with self.lock: 
                    if self.last_choice:
                        self.current = self.last_choice
                        self.past_choices.append(self.last_choice)
                    else: 
                        newnode = self.Choose(TEMPERATURE)
                        self.current = newnode
                        self.past_choices.append(newnode)
                self.state = 1
            if (not self.desire.sitting) and self.state == 1: 
                logging.info("Unsitting, State 1")
                with self.lock:
                    if self.manager.keep1: self.output.SpeakQueue.put(self.manager.keep1)
                    self.manager.keep1 = {}
                for i in range(int(wait)):
                    time.sleep(1)
                    if self.desire.sitting: 
                        logging.info("Sitting again, State 1")
                        break
                if self.desire.sitting: continue
                else:
                    self.state = 2
                    logging.info("Trying Alter, State 1 -> 2")
                    newnode = self.Choose(TEMPERATURE)
                    while newnode in list(self.past_choices): newnode = self.Choose(TEMPERATURE)
                    self.output.SpeakQueue.put(self.llms.Keep2(self.current.data.content, newnode.data.content))
                    for i in range(int(wait*1.5)):
                        time.sleep(1)
                        if self.desire.sitting: 
                            self.current = newnode
                            self.past_choices.append(newnode)
                            logging.info("Sitting again, State 2 -> 1")
                            self.state = 1
                            self.i = 0
                            break
                    if self.desire.sitting: continue
                    else: 
                        logging.info("Gone, State 2 -> 0")
                        with self.lock: self.current = self.root
                        self.state = 0

    # 总控

    def run(self, debug=False) -> None:
        pool = ThreadPool(3)
        pool.spawn(self.EvaluateCoroutine)
        if debug: pool.spawn(self.VisualizeCoroutine)
        threading.Thread(target=self.DisplayThread, daemon=True).start()
        threading.Thread(target=self.StateMachine, daemon=True).start()
        threading.Thread(target=self.StateMachine_0, daemon=True).start()
        threading.Thread(target=self.StateMachine_1, daemon=True).start()
        while True: time.sleep(1800)

    def quit(self) -> None:
        self.output.quit()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    vt = CastratedVolitionTree(True)
    input()
    # o = UI.UI.Output()
    # o.SpeakQueue.put({"en": "a", "zh": "This"})
    # time.sleep(1)
    # o.SpeakQueue.put({"en": "a", "zh": "is"})
    # time.sleep(1)
    # o.SpeakQueue.put({"en": "a", "zh": "A"})
    # time.sleep(1)
    # o.SpeakQueue.put({"en": "a", "zh": "Test"})
    # time.sleep(1)
    # input()