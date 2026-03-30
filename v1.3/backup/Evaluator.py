import numpy as np
from collections import deque

# 这是一个简易的临时评价器。每条记忆存储为向量，模长为价值
# 它的register较慢，evaluate较快
# 实际上，在机器人中，我希望它是通过HNSW实现的，这样就只需要扫描相邻的寥寥几个向量了。

class Evaluator:
    def __init__(self, dim: int, maxlen=100, decline=0.975):
        # 初始化时需要指定向量维度，毕竟要用numpy array
        self.history = deque(maxlen=maxlen)
        self.matrix = np.zeros((1, dim))
        self.decline = decline

    def register(self, vector: np.array, value: float) -> None:
        vector /= np.sqrt(np.sum(np.square(vector)))
        self.history.append(vector*value)
        self.matrix = np.ndarray(list(self.history))

    def evaluate(self, vector: np.array) -> float:
        # 根据历史生成预期评价，返回浮点数
        vector /= np.sqrt(np.sum(np.square(vector)))
        count = 0
        div = 0
        value = 0
        for v in self.history:
            factor = self.decline**count
            value += (v@vector)*factor
            div += factor
            count += 1
        value /= div
        return value
    
    def evaluate2(self, vector: np.array) -> tuple:
        # 带有不确定性的评估。不确定性对于similarity是二次，比value高一次
        vector /= np.sqrt(np.sum(np.square(vector)))
        count = 0
        div = 0
        value = 0
        uncertainty = 0
        ucdiv = 0
        for v in self.history:
            factor = self.decline**count
            similarity = v@vector
            value += similarity*factor
            div += factor
            uncertainty += (similarity*factor)**2
            ucdiv += factor**2
            count += 1
        value /= div
        uncertainty /= ucdiv
        return value, uncertainty
    
    def evaluate3(self, vector: np.array, temperature=1) -> float:
        # 综合不确定性的评估，使用了某种衰减。
        value, uncertainty = self.evaluate2(vector)
        return value*np.exp(-(uncertainty/temperature))