import logging
from datetime import datetime
import json, sys, os
import time
import random, collections, threading
import uuid
from anytree import RenderTree, LevelOrderIter, Node
import numpy as np
import gevent
from gevent.threadpool import ThreadPool
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import func_name, load_json_with_comments, get_filename
import VolitionLib.VolitionNode as VolitionNode
from Processors.LLMAPI import LLM
import IPC
from Processors.Embeddings import Embedder
import VolitionLib.Visualize.API as API

embedder = Embedder()

# 没说上锁就是本函数内没锁，子函数里可能有

class VolitionTree:
    def __init__(self, RootContent: str, treename: str, Threshold=0.3, historyLength=3): 
        self.llms = LLM()
        self.failure = collections.deque(maxlen=historyLength)
        self.success = collections.deque(maxlen=historyLength)
        self.Threshold = Threshold
        self.ipc = IPC.BulletinClient("VolitionTree")
        self.lock = threading.Lock()
        self.settings = load_json_with_comments(os.path.normpath("./settings.json"))
        self.save_dir = os.path.join(os.path.normpath(self.settings["save_dir"]), os.path.normpath(treename))
        os.makedirs(self.save_dir, exist_ok=True)
        self.do_save = self.settings["do_save"]
        self.do_display = self.settings["do_display"]
        self.rootname = "Root"

        if not self.settings["use_saved"]:
            self.root = self.CreateNode(RootContent, self.rootname)
            self.current = self.root
        else:
            filenames = [i for i in get_filename(self.save_dir) if i.startswith(("VT_")) and i.endswith(".json")]
            if filenames: 
                filename = os.path.normpath(max(filenames))
                with open(os.path.join(self.save_dir, filename), "r", encoding="utf-8") as f:
                    JsonData = json.load(f)
                self.root = self.TreeConstructor(JsonData, True)
                self.current = self.root
                self.LoadCurrentPosition()
            else:
                self.root = self.CreateNode(RootContent, self.rootname)
                self.current = self.root
        logging.info(f"{func_name()}: 树初始化完毕")

        self.running = False

        # 用于StateForest管理
        self.activated = False # 初始时未激活
        self.Cooldown = 0.5

    def Activate(self):
        """激活"""
        self.activated = True

    def Deactivate(self):
        """停止"""
        self.activated = False

    def LoadCurrentPosition(self) -> None: 
        """从文件中加载当前所在节点。如果找不到就用已经找到的。
        \n它假设一开始self.current == self.root"""
        with open(os.path.join(self.save_dir, os.path.normpath("CurrentPosition.json")), "r", encoding="utf-8") as f:
            nodepath = json.load(f)
        nodepath.pop()
        nodepath.reverse()
        for node_in_path in nodepath:
            if not self.current.children: return
            found = False
            for child in self.current.children:
                if child.name == node_in_path["id"] and child.data.content == node_in_path["content"]:
                    self.current = child
                    found = True
                    break
            if not found: return

    def SaveVolitionTree(self) -> bool:
        """保存，带锁"""
        try:
            now = datetime.now()
            now = now.strftime("%Y%m%d%H%M%S")
            path = os.path.join(self.save_dir, f"VT_{now}.json")
            logging.info(f"{func_name()}: 开始保存...")
            start = time.time()
            with open(path, "w+", encoding="utf-8") as f: 
                with self.lock: json.dump(VolitionNode.getNodeJson(self.root, True), f)
            logging.info(f"{func_name()}: 保存完毕！用时{time.time()-start}秒")
            return True
        except Exception as e:
            logging.error(f"{func_name}: 保存失败：{e}")
            return False
    
    def SaveCurrentPosition(self) -> None:
        """保存当前所在节点至self.save_dir/CurrentPosition.json，记录路径。带锁。格式：
        \n[{"id":, "content":}, {"id":, "content":}, ... , {"id":, "content":}]"""
        with self.lock: pathlist = self.getKData(-1, True)
        for i in pathlist: i.pop("contentVector", None)
        with open(os.path.join(self.save_dir, os.path.normpath("CurrentPosition.json")), "w+", encoding="utf-8") as f:
            json.dump(pathlist, f)

    def Grow(self) -> bool: 
        """调用LLM给当前节点添加子节点使树生长。必须匹配ID，已锁"""
        with self.lock: 
            targetnode = self.current
            targetid = self.current.name
        First2Volitions = [i["content"] for i in self.getKData(2)]
        JsonData = self.llms.GenerateVolitions(First2Volitions).get("content", 0) 
        if not JsonData: return False
        try:
            # logging.info(JsonData)
            subtree = self.TreeConstructor(JsonData)
            cond = True
            with self.lock: 
                try:
                    if targetnode and targetid == targetnode.name: 
                        for child in subtree.children: child.parent = targetnode
                    else: cond = False
                except Exception as e: 
                    logging.warning(f"{func_name()}: {e}")
                    cond = False
            return cond     
        except Exception as e:
            logging.error(f"{func_name()}: {e}")
            return False
        
    def SelfEvaluate(self, targetVector, m=2, n=2) -> float:
        """取m+1+n层所有节点进行评估，除了根节点"""
        with self.lock:
            current = self.current
            actual_m = 0
            for _ in range(m):
                if current.parent is None: break
                current = current.parent
                actual_m += 1

            total_levels = actual_m + 1 + n
            value = 0.0
            count = 0
            
            for node in LevelOrderIter(current, maxlevel=total_levels):
                if hasattr(node, 'name') and node.name != self.root.name:
                    value += node.data.value*node.data.contentVector@targetVector
                    count += 1

        if count <= 0: 
            # logging.info(f"{func_name()}: 0.0")
            return 0.0
        else: 
            # logging.info(f"{func_name()}: {round(value/count, 2)}")
            return value/count
            
    def Forward(self, temperature=1.0) -> bool: 
        """尝试通过概率采样向下演进，用的softmax，已锁"""
        with self.lock:
            if not self.current.children: 
                logging.info("Didn't Forward")
                return False
            if len(self.current.children) == 1: 
                self.current = self.current.children[0]
                logging.info(f"Forward To: {self.current.data.content}")
                return True
        self.RevalueChildren()
        with self.lock:
            children = self.current.children
            weights = []
            for child in children: weights.append(child.data.value)
            weights = np.array(weights)
            weights = np.exp(weights/temperature)
            self.current = random.choices(children, weights=weights, k=1)[0]
            logging.info(f"Forward To: {self.current.data.content}")
            return True

    def Backward(self, is_completed: bool) -> bool:
        """尝试回退一个节点但不删除原节点及其子节点。根节点无法回退。成功操作则返回True
        \n如果是因为完成了就设置is_completed为true，反之false\n已锁"""
        cond = True
        with self.lock:
            if self.current.name == self.rootname: 
                logging.warning(f"{func_name()}: 到达根")
                cond = False
            else:
                previous = self.current
                self.current = self.current.parent
                if is_completed: self.success.append(VolitionNode.getNodeJson(previous))
                else: self.failure.append(VolitionNode.getNodeJson(previous))
        if cond: logging.info(f"Backward To: {self.current.data.content}")
        else: logging.info(f"Didn't Backward")
        return cond

    def RevalueChildren(self) -> None: 
        """重新评价所有子节点，长耗时"""
        for child in self.current.children: child.data.Revalue()

    def TryAbandonNaive(self, temperature=1) -> bool:
        """这个函数参考threshold和当前节点的价值来计算放弃该意志的概率，随后根据这个概率选择是否放弃，已锁"""
        cond = True
        with self.lock:
            if self.current == self.root: cond = False
            else: value = self.current.data.value
        if not cond: return False
        if value >= self.Threshold: return False
        p = 1-np.exp((value-self.Threshold)/temperature)
        if random.random() <= p: return True
        else: return False

    def getKData(self, k=1, return_root=False) -> list: 
        """获取它自己和k-1阶老妈的内容用于Prompt或用于训练，由子到母。
        \n如果不够k个就把有的输出出来，如果k为-1则输出到达根的路径。"""
        if k == 0: return []
        result = [VolitionNode.getNodeJson(self.current)]
        if k == 1: return result
        if k == -1: ancestors = tuple(reversed(self.current.ancestors))
        else: ancestors = tuple(reversed(self.current.ancestors))[:min(k-1, len(self.current.ancestors))]
        for parent in ancestors: 
            if parent.name == self.rootname and not return_root: continue
            result.append(VolitionNode.getNodeJson(parent))
        return result

    def Visualize(self):
        """可视化整个图，已锁"""
        with self.lock:
            for pre, fill, node in RenderTree(self.root):
                logging.info(f"{pre}{round(node.data.value, 3)}")
        
    def GetRealValue(self) -> float|None:
        """获取真实价值，带锁"""
        with self.lock: message = self.ipc.query_latest_message(receiver="Public_UI_Desire")
        # logging.info(f"{func_name()}: received message {message}")
        if not message["messages"]: return None
        try: return float(message["messages"][0]["content"].strip())
        except ValueError: 
            logging.error(f"{func_name()}: ValueError")
            return None

    # 原隶属于VolitionNode的函数

    def rootevaluate(self, _): return 0.0

    def CreateNode(self, content: str, name=None, is_abstract=True) -> Node:
        """创建一个节点"""
        data = VolitionNode.VolitionData(
            self.SelfEvaluate if name != self.rootname else self.rootevaluate, 
            embedder.embed, 
            content, 
            is_abstract
        )
        if name == None: name = str(uuid.uuid4())
        return Node(name, data=data)

    def LoadNode(self, JsonData) -> Node:
        """从持久化数据读取节点信息，
        \n包括name，content，contentVector，value，is_abstract，time_created
        \n不包括孩子们"""
        return Node(name=JsonData["id"], data=VolitionNode.VolitionData(
            self.SelfEvaluate, embedder.embed, JsonData["content"], JsonData["is_abstract"],
            contentVector=np.array(JsonData["contentVector"]), value=JsonData["value"], 
            time_created=JsonData["time_created"]
        ))
    
    def TreeConstructor(self, JsonData, fulldata=False) -> Node|None:
        """根据Json文件构建一个树，递归"""
        if type(JsonData) == type(""): JsonData = json.loads(JsonData)
        if not JsonData: return
        if not fulldata: current = self.CreateNode(
            content=JsonData.get("content", ""), 
            is_abstract=JsonData.get("is_abstract", True)
        )
        else: current = self.LoadNode(JsonData)
        ChildrenList = JsonData.get("children", [])
        if not ChildrenList: return current
        for child in ChildrenList:
            if type(child) != type({}): continue
            subtree = self.TreeConstructor(child, fulldata)
            if subtree != None: current.children += (subtree,) 
        return current

    # 协程

    def BackwardCoroutine(self, temperature=2.0, cooldown=3.14159265) -> None:
        """这个函数在协程中调用，用于时刻检查是否放弃意志。"""
        while self.running:
            while not self.activated: gevent.sleep(self.Cooldown)
            if self.TryAbandonNaive(temperature): self.Backward(False)
            gevent.sleep(cooldown)

    def ForwardCoroutine(self, temperature=1.0, cooldown=3) -> None:
        """这个函数在协程下运行，用于自动演进"""
        while self.running:
            while not self.activated: gevent.sleep(self.Cooldown)
            self.Forward(temperature)
            gevent.sleep(cooldown)

    def SubmitCoroutine(self, k=2, cooldown=1) -> None: 
        """提交意志到RobotState的协程"""
        while self.running:
            while not self.activated: gevent.sleep(self.Cooldown)
            with self.lock: 
                volitions = self.getKData(k, True)
                volitions = [volition["content"] for volition in volitions]
                # logging.info(f"{func_name()}: {volitions}, {self.current.data.content}")
            self.ipc.post_message("RobotState_Volition", json.dumps(volitions), self.ipc.client_name)
            gevent.sleep(cooldown)

    def EWMACoroutine(self, cooldown=3, rate=0.92) -> None:
        """更新当前节点的价值"""
        while self.running:
            while not self.activated: gevent.sleep(self.Cooldown) # 这里存疑
            rv = self.GetRealValue()
            if rv != None:
                f = lambda x : x*rate+rv*(1-rate)
                with self.lock:
                    if self.current.name != self.root.name: self.current.data.value = f(self.current.data.value)
                    rate = (1+rate)/2
                    if self.current.parent: self.current.parent.data.value = f(self.current.parent.data.value)
                    for nod in self.success: nod.data.value = f(nod.data.value)
            gevent.sleep(cooldown)

    def VisualizeCoroutine(self, cooldown=5) -> None:
        """显示树状态""" # 未启用
        while self.running:
            while not self.activated: gevent.sleep(self.Cooldown)
            self.Visualize()
            gevent.sleep(cooldown)

    # 线程

    def GrowThread(self, cooldown=10) -> None:
        """每过一段时间调用LLM生成一些意志。这个协程的调用频率要小一些，因为要花钱的QAQ"""
        while self.running:
            while not self.activated: time.sleep(self.Cooldown)
            if self.Grow(): pass
            time.sleep(cooldown) # 不用协程所以用time

    def CompletenessThread(self, cooldown1=1, cooldown2=30) -> None: 
        """每过一段时间检查当前意志是否完成，完成则回退。它将匹配节点。有锁"""
        time.sleep(cooldown2)
        while self.running:
            while not self.activated: time.sleep(self.Cooldown)
            cond = True
            with self.lock: 
                id = self.current.name
                if id == self.root.name: cond = False
            if not cond: 
                time.sleep(cooldown1)
                continue
            is_completed = self.llms.Completeness(self.current.data.content)
            if is_completed and id == self.current.name: self.Backward(is_completed)
            if is_completed: time.sleep(cooldown1)
            else: time.sleep(cooldown2)

    def AbandonThread(self, cooldown1=1, cooldown2=30) -> None: 
        """定期尝试放弃的协程，由LLM托管"""
        time.sleep(cooldown2)
        while self.running:
            while not self.activated: time.sleep(self.Cooldown)
            cond = True
            with self.lock: 
                id = self.current.name
                if id == self.root.name: cond = False
            if not cond: 
                time.sleep(cooldown1)
                continue
            do_abandon = self.llms.Abandon(self.current.data.content)
            if do_abandon and id == self.current.name: self.Backward(not do_abandon)
            if do_abandon: time.sleep(cooldown1)
            else: time.sleep(cooldown2)

    def SaveThread(self, cooldown=1800) -> None:
        """定期自动保存，比较耗时所以用线程"""
        if not self.do_save: return
        while self.running:
            while not self.activated: time.sleep(self.Cooldown) # 因为保存还是比较重要的
            time.sleep(cooldown)
            if self.SaveVolitionTree(): self.SaveCurrentPosition()

    def DisplayThread(self, cooldown=1) -> None: # 待完成
        """在前端展示树"""
        if not self.do_display: return
        try: JSAPI = API.API()
        except Exception as e:
            logging.warning(f"{func_name()}: 未启动前端：{e}")
            return
        while self.running:
            while not self.activated: time.sleep(self.Cooldown)
            with self.lock: 
                TreeJsonData = VolitionNode.getNodeJsonVisualization(self.root)
                CurrentID = self.current.name
            JSAPI.Update(TreeJsonData, CurrentID)
            time.sleep(cooldown)

    # 启动

    def run(self):
        self.running = True
        self.Activate()
        # threading.Thread(target=self.GrowThread, daemon=True).start()
        pool = ThreadPool(10)
        pool.spawn(self.SubmitCoroutine)
        pool.spawn(self.ForwardCoroutine)
        pool.spawn(self.EWMACoroutine)
        pool.spawn(self.BackwardCoroutine)
        pool.spawn(self.AbandonThread)
        threading.Thread(target=self.DisplayThread, daemon=True).start()
        threading.Thread(target=self.CompletenessThread, daemon=True).start()
        threading.Thread(target=self.SaveThread, daemon=True).start()
        while self.running: gevent.sleep(600)

    # 退出

    def quit(self) -> None:
        logging.info(f"{func_name()}: 正在退出...")
        self.running = False
        while True:
            if self.SaveVolitionTree(): 
                self.SaveCurrentPosition()
                time.sleep(1)
                break

if __name__ == "__main__": 
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    vt = VolitionTree("", "")
    with open("saves/testtree/VT_20251121164658.json", 'r', encoding='utf-8') as f:
        JsonData = json.load(f)
    root = vt.TreeConstructor(JsonData, fulldata=True)
    JsonData = VolitionNode.getNodeJsonVisualization(root)
    with open("backup/VisualizationJsonData2.json", 'w+', encoding="utf-8") as f:
        json.dump(JsonData, f, ensure_ascii=False, indent=3)