# DM_v1.2_castrated

This is the simplified version of Desiring Machine, it was used for some course project as some installation.  
This version is still a tree structured system, but it contains fixed (frozen) nodes and cannot grow. The content of the nodes are predetermined. However, the nodes are about playing some music or video on the screen, and the LLM will reach out for people around to trigger the "real value" that the bot tries to maximize. So this is kind of fun.  
It is like, the system will keep calling for people around to come along, and if so, they will play some music or video to keep people stay triggering the thing. It is quite like the machine has the desire to make people trigger the thing, such that they will trade people with some services for this.  

## About

This version uses the "K" key to activate positive feedback (sitting). **Note that the subtitle may not work well in this mode.**

If you have the hardware, change line 39 of "main.py" from "True" to "False". 

## Install

**Use Windows !!!**

### Step 1: Install FFMPEG

Download the official static version of the build (https://ffmpeg.org/download.html). 
After decompression, add its bin directory to the system environment variable PATH.

### Step 2: Install Python Libraries

```cmd
pip install -r requirements.txt
```

## How To Run

### Step 1: API setting

Fill in the LLM APIs in the "settings.json".  

### Step 2: Run

In the main directory:
```cmd
python main.py
```

## If You Have the Hardware

Use a Type-C to connect it to the computer, use the "COM" portal. Run "sensor_testing.py" for testing the sensor. The threshold of detecting whether the participant is sitting is 400 mm.
To run the project with this hardware, change line 39 of "main.py" from 
```python
VT = CastratedVolitionTree(True)
```
to
```python
VT = CastratedVolitionTree(False)
```

The hardwares are:   
ESP32-S3N16R8 (Motherboard)  
GY-530 VL53L0X (Laser Sensor)