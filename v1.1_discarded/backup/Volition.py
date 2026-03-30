import random, uuid, collections
from anytree import Node, RenderTree
import numpy as np
import time, logging
from lib_helper import func_name

# 在处理的时候应该需要使用协程，因为要和处理队列并行
# 在添加节点之前，必须要匹配一下节点的id



def evaluate(content: str):
    # 一个用于模拟价值评估的假函数
    return 1

class VolitionData:
    def __init__(self, content, value, is_abstract=True, code=None):
        self.content = content
        self.value = value
        self.is_abstract = is_abstract
        self.code = code # 这个code是只有具体节点才有的，它需要是能够直接处理的指令

class VolitionTree:
    def __init__(self, RootContent, historyLength=5):
        root = VolitionData(RootContent, None)
        self.root = Node("Root", data=root)
        self.current = self.root
        self.failure = collections.deque(maxlen=historyLength)
        self.success = collections.deque(maxlen=historyLength)

    def getNodeJson(self, node):
        # 格式：{ "id": , "content": , "is_abstract": , "code":  }
        return {
            "id": node.name,
            "content": node.data.content,
            "is_abstract": node.data.is_abstract,
            "code": "" if node.data.is_abstract else node.data.code
        }

    def Add(self, content, value, current_id, is_abstract=True) -> bool:
        # 给当前节点添加孩子，必须id匹配且abstract才行
        if (current_id != self.current.name) or (not self.current.data.is_abstract): 
            logging.warning(f"{func_name}: 节点ID不匹配或节点具体，无法添加孩子")
            return False
        data = VolitionData(content, value, is_abstract)
        Node(str(uuid.uuid4()), data=data, parent=self.current)
        return True

    def Forward(self, temperature = 1.0) -> bool:
        # 尝试通过概率采样向下演进，用的softmax
        if not self.current.children: return False
        if len(self.current.children == 1): 
            self.current = self.current.children[0]
            return True
        self.Revalue()
        children = self.current.children
        weights = []
        for child in children: weights.append(child.data.value)
        weights = np.array(weights)
        weights = np.exp(weights/temperature)
        self.current = random.choices(children, weights=weights, k=1)[0]
        return True
    
    def Backward(self, is_completed: bool) -> bool:
        # 尝试回退一个节点并删除原节点及其子节点，这个如果意志完成了也要用到，但设置参数为True
        if self.current.name == "Root": 
            logging.warning(f"{func_name()}: 到达根")
            return False
        previous = self.current
        self.current = self.current.parent
        if is_completed: self.success.append(self.getNodeJson(previous))
        else: self.failure.append(self.getNodeJson(previous))
        previous.parent = None
        self.Revalue()
        return True

    def Progress(self, timeout=30, cooldown=1) -> bool:
        # 演进，timeout后无法演进则退回
        starttime = time.time()
        while True:
            if self.Forward(): return True
            time.sleep(cooldown)
            if time.time() - starttime >= timeout: break
        logging.info(f"{func_name()}: 演进失败，回退一次")
        self.Backward(False)
        return False

    def Revalue(self) -> None:
        # 重新评价所有子节点
        for child in self.current.children:
            child.data.value = evaluate(child.data.content)

    def getKData(self, k) -> list:
        # 获取它自己和k-1阶老妈的内容用于Prompt或用于训练，由子到母，如果不够k个就把有的输出出来。不输出根。
        if k <= 0: return []
        result = [self.getNodeJson(self.current)]
        if k == 1: return result if self.current.name != "Root" else []
        ancestors = self.current.ancestors[:min(k-1, len(self.current.ancestors))]
        for parent in ancestors: 
            if parent.name == "Root": continue
            result.append(self.getNodeJson(parent))
        return result

    def Visualize(self):
        # 可视化整个图
        for pre, fill, node in RenderTree(self.root):
            print(f"{pre}{node.data.content}")
            logging.info(f"{pre}{node.data.content}")