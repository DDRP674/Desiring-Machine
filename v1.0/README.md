# DM_v1.0

# Intro

This is the first version of Desire Machine. It is a tree-structured system that starts from a simple base node (defaultly, "make me happy"), and the reward (desire) would be "pressing the K key".  

This version is quite rough, we recommend for other versions for testing.  

## Node Value

Every node (volition) in the tree has its own "value", and the value will control whether the current volition considered by the bot will be deleted or not, or will the current volition shift to its child nodes, and which child node will it shift to. In our design, child nodes with higher value will have higher probability to be shifted to, and thus become the new current volition node.    
The value will gradually shift to the "real value" the bot is sensing, which is exactly the variable that the bot is intended to try to maximize, i.e., whether the K key is being pressed. However, every node has an "assumed" value, which is the value that the bot believes it should be. This value will be generated for child nodes when shifting is required, or generated for new nodes. This value will come from the "Evaluator".  

## Evaluator

Evaluator is a simple vector database that will provide historical information about the value of past volitions, and it will help decide how much the value a volition should be.   
It contains $k$ past volitions, including their embedding vector $u_i$ and their eventual value $v_i$, stored in a heap. Given a volition with embedding $u^*$, the value will be:

$$
v^* = \frac{\sum_i (u_i^T u^* \cdot v_i)}{\sum_i u_i^T u^*}
$$

Thus, only the related historical volitions can have larger impact on the value of this target volition.  