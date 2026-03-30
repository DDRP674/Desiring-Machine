# About

This is the simplified version of Desiring Machine. It only uses a small amount of the originally used videos and musics to remain a small size. 

This version uses the "K" key to activate positive feedback (sitting), only for testing and grading. **Note that the subtitle may not work well in this mode.**

If you have the hardware, change line 39 of "main.py" from "True" to "False". 

# Statements

**This source code is solely for the purpose of authorized course assignment grading.**  

**Any other usages, including but not limited to copying, sharing, distributing, or posting online, are strictly prohibited.**

# Install

**Use Windows !!!**

## Step 1: Install FFMPEG

Download the official static version of the build (https://ffmpeg.org/download.html). 
After decompression, add its bin directory to the system environment variable PATH.

## Step 2: Install Python Libraries

```cmd
pip install -r requirements.txt
```

# How To Run

## Step 1: API setting

Fill in the LLM APIs in the "settings.json".  

## Step 2: Run

In the main directory:
```cmd
python main.py
```

# If You Have the Hardware

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