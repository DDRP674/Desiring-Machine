from anytree import Node

# 创建多层树结构
root = Node("root")
level1 = Node("level1", parent=root)
level2 = Node("level2", parent=level1)
level3 = Node("level3", parent=level2)
level4 = Node("level4", parent=level3)

print("树结构:")
print(f"root → level1 → level2 → level3 → level4")

print(level4.ancestors)
print(tuple(reversed(level4.ancestors)))