# DM_v1.2

This version is a rather complete version.

## Self Evaluation

Instead of using an external heap-structured vector database as evaluator, this version uses the n+m+1 layer subtree of which the root node is the m-th parent node of current node, to evaluate some nodes' value.  
The nodes in the subtree will construct a set of embedding vectors and values which will calculate the new value in the same way as before.  

## Visualization

I also made a little visualization for the tree in JS, so you can see it grow.  