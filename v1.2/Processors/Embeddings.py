import logging
from sentence_transformers import SentenceTransformer

# 本来这个应该搞个Queue的，但后来想想还是算了，没必要。如果需要了再说。现在Embedding一个句子基本上都在200毫秒以下。

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer('BAAI/bge-base-en-v1.5') # 加载模型
        self.dim = self.model.encode("").shape[0] # 测试

    def embed(self, content): 
        logging.info("Embedding content: " + content)
        return self.model.encode(content)
    
if __name__ == "__main__":
    import time
    e = Embedder()
    start = time.time()
    v1 = e.embed("Express excitement about the user's participation")
    duration = time.time() - start
    print(f"嵌入耗时：{duration}")
    v2 = e.embed("Express excitement about the user's participation")
    v3 = e.embed("Fuck my life")
    v4 = e.embed("Express disgust about the user's absense")
    print(v1@v2)
    print(v1@v3)
    print(v1@v4)