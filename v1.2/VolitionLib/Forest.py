import logging
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import IPC

# 尚未启用

class Forest:
    def __init__(self): 
        self.trees = {}
        self.ipc = IPC.BulletinClient("StateForest")
        self.activating_tree_name = None

    def add_tree(self, tree) -> bool: 
        if self.trees.get(tree.treename, None) != None: 
            logging.warning("添加树失败：已存在树")
            return False
        self.trees[tree.treename] = tree
        return True

    def SwitchTo(self, treename: str) -> bool:
        if self.trees.get(treename, None) == None: 
            logging.warning("调整至树失败：不存在树")
            return False    
        if self.activating_tree_name != None: self.trees[self.activating_tree_name].Deactivate()
        self.trees[treename].Activate()
        self.activating_tree_name = treename
        return True
        
    