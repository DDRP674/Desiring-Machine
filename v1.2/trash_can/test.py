import anytree

def getKData(node, k=1) -> list: # bug
        """获取它自己和k-1阶老妈的内容用于Prompt或用于训练，由子到母。
        \n如果不够k个就把有的输出出来，如果k为-1则输出到达根的路径。"""
        # 有bug，大概是reverse导致的，submitsubmit错了
        if k == 0: return []
        result = [node.name]
        if k == 1: return result
        if k == -1: ancestors = tuple(reversed(node.ancestors))
        else: ancestors = tuple(reversed(node.ancestors))[:min(k-1, len(node.ancestors))]
        for parent in ancestors: result.append(parent.name)
        return result

root = anytree.Node("root")
n1 = anytree.Node("1", parent=root)
n2 = anytree.Node("2", parent=n1)
n3 = anytree.Node("3", parent=n2)

print(getKData(n3, k=5))