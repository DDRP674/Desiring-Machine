from threading import Lock
import time, json
import datetime, logging, uuid
import sys, os
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib_helper import func_name
from anytree import Node
from Processors.Evaluator import Evaluator
from Processors.Embeddings import Embedder

embedder = Embedder()
evaluator = Evaluator(embedder.dim)
lock = Lock()

def getNodeJson(node: Node, fullmode=False):
    """格式：{ "id": , "content": , "contentVector": }\n
    完整格式：{ "id": , "content": , "contentVector": , "value": , "is_abstract": , \n
    "time_created": , "children": [] }""" 
    if not fullmode: return {
        "id": node.name,
        "content": node.data.content,
        "contentVector": node.data.contentVector.tolist()
    }
    else: return {
        "id": node.name,
        "content": node.data.content,
        "contentVector": node.data.contentVector.tolist(),
        "value": node.data.value,
        "is_abstract": node.name,
        "time_created": node.data.time_created,
        "children": [getNodeJson(child, fullmode) for child in node.children] if node.children else []
    }

def CreateNode(content: str, name=None, is_abstract=True, evaluator=evaluator.evaluate3) -> Node:
    """创建一个节点"""
    data = VolitionData(evaluator, embedder.embed, content, is_abstract)
    if name == None: name = str(uuid.uuid4())
    return Node(name, data=data)

def LoadNode(JsonData, evaluator=evaluator.evaluate3) -> Node:
    """从持久化数据读取节点信息，
    \n包括name，content，contentVector，value，is_abstract，time_created
    \n不包括孩子们"""
    return Node(name=JsonData["id"], data=VolitionData(
        evaluator, embedder.embed, JsonData["content"], JsonData["is_abstract"],
        contentVector=np.array(JsonData["contentVector"]), value=JsonData["value"], 
        time_created=JsonData["time_created"]
    ))

def AddNode(node: Node, content: str, is_abstract=True) -> bool:
    """给某个节点添加孩子"""
    if not node.data.is_abstract: 
        logging.warning(f"{func_name}: 具体节点无法添加孩子")
        return False
    NewNode = CreateNode(content=content, is_abstract=is_abstract)
    NewNode.parent = node
    return True

def TreeConstructor(JsonData, fulldata=False, evaluator=evaluator.evaluate3) -> Node|None:
    """根据Json文件构建一个树，递归"""
    if type(JsonData) == type(""): JsonData = json.loads(JsonData)
    if not JsonData: return
    if not fulldata: current = CreateNode(
        content=JsonData.get("content", ""), 
        is_abstract=JsonData.get("is_abstract", True),
        evaluator=evaluator
    )
    else: current = LoadNode(JsonData, evaluator=evaluator)
    ChildrenList = JsonData.get("children", [])
    if not ChildrenList: return current
    for child in ChildrenList:
        if type(child) != type({}): continue
        subtree = TreeConstructor(child, fulldata, evaluator=evaluator)
        if subtree != None: current.children += (subtree,) 
    return current

class VolitionData:
    def __init__(self, evaluator, embedding, content: str, is_abstract=True, 
                 contentVector=np.array([]), value=None, time_created=None):
        """evaluator和embedding是函数"""
        self.content = content
        self.evaluator = evaluator
        if contentVector.shape == (0,): self.contentVector = embedding(self.content) #这个由embedding负责
        else: self.contentVector = contentVector
        if value == None: self.value = evaluator(self.contentVector)
        else: self.value = value
        now = datetime.datetime.now()
        if time_created == None: self.time_created = now.strftime("%Y%m%d%H%M%S")
        else: self.time_created = time_created
        self.is_abstract = is_abstract

    def Revalue(self): 
        """重新评估，各个节点共用一个锁"""
        with lock: self.value = self.evaluator(self.contentVector)


if __name__ == "__main__":
    import json
    from anytree import RenderTree

    with open("backup/VolitionJsonDataSample.json", "r", encoding="utf-8") as f: 
        JsonData = json.load(f)
    def g(a): return
    start = time.time()
    root = TreeConstructor(JsonData)
    end = time.time() - start
    for pre, fill, node in RenderTree(root): print(f"{pre}{node.data.contentVector.shape}")
    print(f"构建树耗时：{end}秒")
    