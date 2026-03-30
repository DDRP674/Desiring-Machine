from numpy import log

def tofloat(value, default=0.0):
    if value is None: return default
    try:
        if hasattr(value, 'item'): return float(value.item())
        else: return float(value)
    except (ValueError, TypeError): return default

def getNodeJsonVisualization(node):
    """格式：{"id": , "value": "children": []}"""
    value = (log(80*node.data.value+1)/log(9))-1
    return {
        "id": node.name,
        "value": tofloat(value),
        "children": [getNodeJsonVisualization(child) for child in node.children] if node.children else []
    }

class VolitionData:
    """本身无锁"""
    def __init__(self, content: str):
        self.content = content
        self.Asking = ""
        self.Keeping = ""
        self.value = 0.1
