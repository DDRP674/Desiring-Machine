from datetime import datetime
import json, sys, os
import time
import random, collections, threading
from anytree import RenderTree
import numpy as np
import logging, gevent
from gevent.threadpool import ThreadPool
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import func_name, load_json_with_comments, get_filename
import VolitionLib.VolitionNode as VolitionNode
from Processors.LLMAPI import LLM
import IPC

# 没说上锁就是本函数内没锁，子函数里可能有

def GetCurrentRealValue() -> float:
    """模拟欲望实在的行为"""
    return 0.0

class VolitionTree:
    def __init__(self, RootContent: str, Threshold = 0.5, historyLength=3): 
        self.llms = LLM()
        self.failure = collections.deque(maxlen=historyLength)
        self.success = collections.deque(maxlen=historyLength)
        self.Threshold = Threshold
        self.ipc = IPC.BulletinClient("VolitionTree")
        self.lock = threading.Lock()
        self.settings = load_json_with_comments(os.path.normpath("./settings.json"))
        self.save_dir = os.path.normpath(self.settings["save_dir"])
        self.do_save = self.settings["do_save"]

        if not self.settings["use_saved"]:
            self.root = VolitionNode.CreateNode(RootContent, "Root")
            self.current = self.root
        else:
            filename = os.path.normpath(max([i for i in get_filename(self.save_dir) 
                         if i.startswith(("VT_")) and i.endswith(".json")]))
            with open(os.path.join(self.save_dir, filename), "r", encoding="utf-8") as f:
                JsonData = json.load(f)
            self.root = VolitionNode.TreeConstructor(JsonData, True)
            self.current = self.root
            self.LoadCurrentPosition()

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
                if child.name == node_in_path["id"] and child.content == node_in_path["content"]:
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
                with self.lock: json.dump(VolitionNode.getNodeJson(self.root, True), f, ensure_ascii=True)
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
            json.dump(pathlist, f, ensure_ascii=True)

    def Grow(self) -> bool: 
        """调用LLM给当前节点添加子节点使树生长。必须匹配ID，已锁"""
        with self.lock:
            current_id = self.current.name
        First2Volitions = [i["content"] for i in self.getKData(2)]
        JsonData = self.llms.GenerateVolitions(First2Volitions).get("content", 0)
        if not JsonData: return False
        try:
            logging.info(JsonData)
            subtree = VolitionNode.TreeConstructor(JsonData)
            cond = True
            with self.lock:
                if (current_id != self.current.name): 
                    logging.warning(f"{func_name()}: 节点ID不匹配，无法添加孩子")
                    cond = False
                else: 
                    for child in subtree.children: 
                        child.parent = self.current
            return cond     
        except Exception as e:
            logging.error(f"{func_name()}: {e}")
            return False

    def Forward(self, temperature=1.0) -> bool:
        """尝试通过概率采样向下演进，用的softmax，已锁"""
        with self.lock:
            if not self.current.children: return False
            if len(self.current.children) == 1: 
                self.current = self.current.children[0]
                return True
        self.RevalueChildren()
        with self.lock:
            children = self.current.children
            weights = []
            for child in children: weights.append(child.data.value)
            weights = np.array(weights)
            weights = np.exp(weights/temperature)
            self.current = random.choices(children, weights=weights, k=1)[0]
            return True

    def Backward(self, is_completed: bool) -> bool:
        """尝试回退一个节点并删除原节点及其子节点，根节点无法完成。成功操作则返回True
        \n如果是因为完成了就设置is_completed为true，反之false\n已锁"""
        cond = True
        with self.lock:
            if self.current.name == "Root": 
                logging.warning(f"{func_name()}: 到达根")
                cond = False
            else:
                previous = self.current
                self.current = self.current.parent
                if is_completed: self.success.append(VolitionNode.getNodeJson(previous))
                else: self.failure.append(VolitionNode.getNodeJson(previous))
                previous.parent = None
        if cond: self.RevalueChildren()
        return cond

    def RevalueChildren(self) -> None:
        """重新评价所有子节点，长耗时"""
        for child in self.current.children: child.data.Revalue()

    def TryAbandonNaive(self, temperature=1) -> bool:
        """这个函数参考threshold和当前节点的价值来计算放弃该意志的概率，随后根据这个概率选择是否放弃，已锁"""
        cond = True
        with self.lock:
            if self.current == self.root: cond = False
            else:
                self.current.data.Revalue()
                value = self.current.data.value
        if not cond: return False
        if value >= self.Threshold: return False
        p = 1-np.exp((value-self.Threshold)/temperature)
        if random.random() <= p: return True
        else: return False

    def TryAbandon(self): # 待完成
        """尝试放弃，LLM托管"""

    def getKData(self, k=1, return_root=False) -> list:
        """获取它自己和k-1阶老妈的内容用于Prompt或用于训练，由子到母。
        \n如果不够k个就把有的输出出来，如果k为-1则输出到达根的路径。"""
        if k == 0: return []
        result = [VolitionNode.getNodeJson(self.current)]
        if k == 1: return result
        if k == -1: ancestors = self.current.ancestors
        else: ancestors = self.current.ancestors[:min(k-1, len(self.current.ancestors))]
        for parent in ancestors: 
            if parent.name == "Root" and not return_root: continue
            result.append(VolitionNode.getNodeJson(parent))
        return result

    def Visualize(self):
        """可视化整个图，已锁"""
        with self.lock:
            for pre, fill, node in RenderTree(self.root):
                logging.info(f"{pre}{node.data.content}")
        
    # 协程

    def BackwardCoroutine(self, temperature=1.0, cooldown=1) -> None:
        """这个函数在协程中调用，用于时刻检查是否放弃意志。它在程序运行之初就运行"""
        """它的cooldown决定了尝试放弃的频率"""
        while True:
            if self.TryAbandonNaive(temperature): self.Backward(False)
            gevent.sleep(cooldown)

    def ForwardCoroutine(self, temperature=1.0, cooldown=3) -> None:
        """这个函数在协程下运行，用于自动演进"""
        while True:
            self.Forward(temperature)
            gevent.sleep(cooldown)

    def SubmitCoroutine(self, k=2, cooldown=1) -> None: 
        """提交意志到RobotState的协程"""
        while True:
            self.ipc.post_message("RobotState", json.dumps(self.getKData(k)), self.ipc.client_name)
            gevent.sleep(cooldown)

    def EvaluatorUpdateCoroutine(self, with_history=True, cooldown=10) -> None:
        """每隔一段时间向评估器发送历史，包括当前意志和历史意志，以随机次序进去"""
        while True:
            with self.lock: 
                id = self.current.name
                rootid = self.root.name
            if id == rootid: continue
            with self.lock:
                if with_history:
                    ls = [i["contentVector"] for i in self.success]
                    random.shuffle(ls)
                    # 没有处理失败的记忆，大概是因为没有做成的事情不会对未来造成影响罢
                    l = [self.current.data.contentVector] + ls
                else: l = [self.current.data.contentVector]
            rv = GetCurrentRealValue()
            for i in l: VolitionNode.evaluator.register(i, rv)
            gevent.sleep(cooldown)

    def EvaluateCoroutine(self, cooldown=3) -> None:
        """自动重新评估当前节点"""
        while True:
            self.current.data.Revalue()
            gevent.sleep(cooldown)

    def DisplayCoroutine(self, cooldown=5) -> None:
        """显示树状态"""
        while True:
            self.Visualize()
            gevent.sleep(cooldown)

    # 线程

    def GrowThread(self, cooldown=10) -> None:
        """每过一段时间调用LLM生成一些意志。这个协程的调用频率要小一些，因为要花钱的QAQ"""
        while True:
            self.Grow()
            time.sleep(cooldown) # 不用协程所以用time

    def CompletenessThread(self, cooldown=3) -> None: 
        """每过一段时间检查当前意志是否完成，完成则回退。它将匹配节点。有锁"""
        while True:
            cond = True
            with self.lock: 
                id = self.current.name
                if id == self.root.name: cond = False
            if not cond: continue
            is_completed = self.llms.Completeness(self.current.data.content)
            if is_completed and id == self.current.name: self.Backward(is_completed)
            time.sleep(cooldown) # 不用协程所以用time

    def AbandonThread(self, cooldown=3) -> None: # 待完成
        """定期尝试放弃的协程，由LLM托管"""
        while True:
            gevent.sleep(cooldown)

    def SaveThread(self, cooldown=1800) -> None:
        """定期自动保存，比较耗时所以用线程"""
        if not self.do_save: return
        while True:
            time.sleep(cooldown)
            if self.SaveVolitionTree(): self.SaveCurrentPosition()

    # 启动

    def run(self):
        threading.Thread(target=self.GrowThread, daemon=True).start()
        pool = ThreadPool(10)
        pool.spawn(self.SubmitCoroutine)
        pool.spawn(self.ForwardCoroutine)
        pool.spawn(self.EvaluateCoroutine)
        pool.spawn(self.BackwardCoroutine)
        pool.spawn(self.EvaluatorUpdateCoroutine)
        pool.spawn(self.DisplayCoroutine)
        pool.spawn(self.AbandonThread)
        threading.Thread(target=self.CompletenessThread, daemon=True).start()
        threading.Thread(target=self.SaveThread, daemon=True).start()
        while True: gevent.sleep(600)

    # 退出

    def quit(self) -> None:
        logging.info(f"{func_name()}: 正在退出...")
        while True:
            if self.SaveVolitionTree(): 
                self.SaveCurrentPosition()
                break

if __name__ == "__main__": VolitionTree("")