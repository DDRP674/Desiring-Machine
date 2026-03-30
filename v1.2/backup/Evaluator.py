import logging
import numpy as np
from collections import deque
from threading import Lock

# 这是一个简易的临时评价器。每条记忆存储为向量，模长为价值
# 它的register较慢，evaluate较快。实际上使用环形矩阵可以让两个都快。
# 实际上，在机器人中，我希望它是通过HNSW实现的，这样就只需要扫描相邻的寥寥几个向量了。
# 为了减小非相似记忆的影响，目前使用了立方缩放。也许使用ReLU更好。

class Evaluator:
    def __init__(self, dim: int, maxlen=1000, decline=0.997):
        """初始化时需要指定向量维度，毕竟要用numpy array"""
        self.history = deque(maxlen=maxlen)
        self.matrix = np.zeros((1, dim))
        self.decline = decline
        self.lock = Lock()
        self.RegisterCounter = 0

    def register(self, vector: np.array, value: float) -> None:
        """往评估器中添加记忆向量，这个大概只有在一个意志节点被删除时调用"""
        if type(vector) != type(np.array([])): vector = np.array(vector)
        vector /= np.sqrt(np.sum(np.square(vector)))
        with self.lock:
            self.history.append(vector*value) 
            temp = self.history
        self.RegisterCounter += 1
        if self.RegisterCounter >= 3:
            matrix = np.vstack(temp)
            self.RegisterCounter = 0
            with self.lock: self.matrix = matrix
        # logging.info("Evaluator: registered new memory, total memories: {}".format(len(self.history)))

    def evaluate(self, vector: np.array) -> float:
        """根据历史生成预期评价，返回浮点数"""
        if type(vector) != type(np.array([])): vector = np.array(vector)
        vector /= np.sqrt(np.sum(np.square(vector)))
        with self.lock: similarityVector = (self.matrix@vector)
        decay_factors = np.power(self.decline, np.arange(len(similarityVector)))
        value = (similarityVector@decay_factors)/np.sum(decay_factors)
        return value
    
    def evaluate2(self, vector: np.array) -> tuple:
        if type(vector) != type(np.array([])): vector = np.array(vector)
        vector /= np.linalg.norm(vector)
        with self.lock: similarityVector = (self.matrix@vector)
        decay_factors = np.power(self.decline, np.arange(len(similarityVector)))
        value = (similarityVector@decay_factors)/np.sum(decay_factors)
        deviations = similarityVector-value
        variance = np.sum((deviations*decay_factors)**2) / np.sum(decay_factors**2)
        return value, variance # variance关于实际价值比value高一次
    
    def evaluate3(self, vector: np.array, temperature=10) -> float:
        """综合不确定性的评估，使用了某种衰减。"""
        value, uncertainty = self.evaluate2(vector)
        value = value*np.exp(-(uncertainty/temperature))
        # logging.info("Evaluator: evaluated memory with value {:.4f} and uncertainty {:.4f}, final value {:.4f}".format(value, uncertainty, value))
        return value