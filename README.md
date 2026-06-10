# Desiring Machine

# Intro

This is an experimental agentic system built for putting my artifical intelligence and philosophy ideas into practice. It started from 2025.9. At that time I was still a noob coder, so you can see some of the implementations are naive or not elegant.  

You may wonder what is a Desiring Machine. **It is a system that simulates the mechanism of desire of human beings, or other entities.**  

*To a system: Complexity of Output = max(Complexity of the system structure, Complexity of the environment)*  

I planned to develop a system that starts from a simple "desire", which is similar to the concept "reward" in reinforcement learning or in psychology.  
**We set up a simple variable, and let the system adjust the behaviour (policy, or strategy), to make the variable to be maximized (or minimized).**  

This is some kind of reinforcement learning, but the difference is that the learning process is done not by hardcore mathematical algorithms, but by an "evolution" of prompt instructions (we call it "volition", it is **texts of instructions that can be both input (used as prompt) or output (generated) by LLMs**).  
We would like to see the system evolves from a simple "desire", into a complex and maybe "clever" system, under the complexity of the environment.  

This evolution is simple: the volitions that maximizes the reward tend to persist, while the opposite kinds tend to vanish.  
We believe the human behaviour, thoughts, ideologies are generated in this way as well: **Combining memory and environmental feedback information from the senses, under the drive of brain reasoning, generate and execute volitions and behaviors that are more likely to be rewarded in the short or long term**  
And this mechanism eventually constructed human history, philosophy, science, art, and any other things in the human world.  
Thus, you may regard it as a model of human, an *"abstracted human being that only retain the most basic features: Desire"*  

# Design

Here's a simple poster:  
![poster](./Poster.jpg)

## Volition Pool

There are many ways to make the volitions evolve. We can treat the volitions as texts of instructions that can be both input (used as prompt) or output (generated) by LLMs.  

And then, a naive way of evolving is that we set up a pool with limited size that contains multiple volitions, in which more useful (rewarded) volitions persists, and less useful volitions gets kicked out.  

## Volition Stack

However, maintaining such a pool for volition may be token-consuming. Also, human behaviours are with inheritance relationships, e.g., working is for making money, making money is for buying food, buying food is for eating...  
Hence, we consider a stack to contain the volitions, that the bottom of the stack is the most abstract volition (we call this the desire); and the top of the stack is the volition usually indicates what to do.  
Consider two adjacent volitions in the stack, the higher volition is generated in order to do the lower one, and only the volition in the top can be generated, modified, or canceled, by the "usefulness" defined by reward. As the bottom volition is the desire (which indicates maximizing the reward), **the whole stack of volition will be based on this desire, although volitions in higher positions will not seem like it.**  

This is somehow aligned to human behaviours, that usually human beings fails to thoroughly explain what their behaviours are for. I gotta say this has something to do with psychoanalysis.  

## Volition Tree

We may naturally think of tree-structure when we see stacks.  
When we generate multiple, instead of one volition, for inheritance of lower volitions, it will be a Volition Tree.  

**This is where "Complexity" comes out. It grows larger and larger.**

**There are currently five versions of this system, they are all tree-structured.** You may find introductions in each of the folders. You may want some assistance from coding agents or from me when you are trying to run them.  

# Future Works

I can't say there will be a future work. However, a **Volition Graph** can be an advanced system of this project, that volitions can construct a graph, where the current behaviour of a bot is "swimming" in the graph.  
**The Forest of Volition Tree** can also be considered. There will surely be more fun if we let multiple trees control the behaviour of a bot.  
Also, volition tree can be developped into a new form of long-term memory system for bots. I tend to call it **"The World Tree"**.  

# Some Philosophy

Human beings are desire machines, the desire mechanism (i.e., human behaviour evolves according to rewards) is the basic of human.  

Everything involves human, everything in the human world, is largely impacted, or even based on desire mechanism.  

If we develop a computer system that have this desire mechanism as well, it may behave like human beings in a more fundamental way.  

And if we can study or modify this desire, we may have a deeper understanding of human beings, intelligence, or even discover things beyond our understandings.   

