from threading import Lock
import datetime
import sys, os
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

lock = Lock()

def tolist(array):
        if array is None: return None
        return np.asarray(array).astype(float).tolist()

def tofloat(value, default=0.0):
    if value is None: return default
    try:
        # 如果是numpy类型，使用item()转换为Python原生类型
        if hasattr(value, 'item'): return float(value.item())
        # 如果是Python类型，直接转换
        else: return float(value)
    except (ValueError, TypeError): return default

def getNodeJson(node, fullmode=False):
    """格式：{ "id": , "content": , "contentVector": }\n
    完整格式：{ "id": , "content": , "contentVector": , "value": , "is_abstract": , \n
    "time_created": , "children": [] }""" 
    if not fullmode: return {
        "id": node.name,
        "content": node.data.content,
        "contentVector": tolist(node.data.contentVector)
    }
    else: return {
        "id": node.name,
        "content": node.data.content,
        "contentVector": tolist(node.data.contentVector),
        "value": tofloat(node.data.value),
        "is_abstract": node.name,
        "time_created": node.data.time_created,
        "children": [getNodeJson(child, fullmode) for child in node.children] if node.children else []
    }

def getNodeJsonVisualization(node):
    """格式：{"id": , "value": "children": []}"""
    return {
        "id": node.name,
        "value": tofloat(node.data.value),
        "children": [getNodeJsonVisualization(child) for child in node.children] if node.children else []
    }


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


if __name__ == "__main__": pass
    