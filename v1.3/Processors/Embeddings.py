import logging
from sentence_transformers import SentenceTransformer
import numpy as np

# 本来这个应该搞个Queue的，但后来想想还是算了，没必要。如果需要了再说。现在Embedding一个句子基本上都在200毫秒以下。

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer('BAAI/bge-base-en-v1.5') # 加载模型
        self.dim = self.model.encode("").shape[0] # 测试

    def embed(self, content): 
        """默认归一化"""
        logging.info("Embedding content: " + content)
        vector = self.model.encode(content)
        return vector/(np.sum(vector**2))**0.5
    
if __name__ == "__main__":
    import time
    e = Embedder()
    start = time.time()
    v = e.embed("Express excitement about the user's participation")
    end = time.time()
    print(f"Embedding took {end - start:.2f} seconds")