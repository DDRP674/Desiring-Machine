from sentence_transformers import SentenceTransformer

# 本来这个应该搞个Queue的，但后来想想还是算了，没必要。如果需要了再说。现在Embedding一个句子基本上都在200毫秒以下。

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer('BAAI/bge-base-en-v1.5') # 加载模型
        self.dim = self.model.encode("").shape[0] # 测试

    def embed(self, content):
        return self.model.encode(content)