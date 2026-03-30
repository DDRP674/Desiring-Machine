import time
from anytree import Node, PreOrderIter

def benchmark_tree_traversal(root, desc="Traversal"):
    start = time.perf_counter()
    node_count = 0
    for node in PreOrderIter(root):
        # 模拟你的业务操作
        _ = node.name
        _ = node.depth
        node_count += 1
    elapsed = time.perf_counter() - start
    
    print(f"{desc}: {node_count} nodes in {elapsed:.3f}s "
          f"({node_count/elapsed:,.0f} nodes/sec)")
    return elapsed

benchmark_tree_traversal(Node("root", children=[Node(f"child{i}") for i in range(70000)]), "Test Tree Traversal")