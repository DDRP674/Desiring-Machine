################################################################
# PROXIMITY SENSOR HARDWARE INTERFACE
# Version: V2.0 (Ultra Low Latency)
# Hardware: ESP32-S3 + VL53L0X ToF Laser Sensor
################################################################

[1] QUICK START
----------------------------------------------------------------
1. Connect the device via USB-C.
   * IMPORTANT: Use the LEFT port labeled 'COM'.
   * The RIGHT port ('USB') is for debugging only.

2. Ensure Python dependencies are installed:
   > pip install pyserial

3. Run the test script to verify data flow:
   > python sensor_api.py


[2] DRIVER INSTALLATION (REQUIRED)
----------------------------------------------------------------
If the device is not detected or connection fails, you must install 
the USB-UART driver corresponding to the onboard chipset.

The hardware typically uses the CH340 chipset.

- Windows Driver (CH340): 
  http://www.wch.cn/downloads/CH341SER_EXE.html
  Action: Download -> Run -> Click "INSTALL".

*Verification*: 
Open Device Manager -> Ports (COM & LPT). 
You should see "USB-SERIAL CH340 (COMx)" when the device is plugged in.


[3] API INTEGRATION GUIDE
----------------------------------------------------------------
1. Place 'sensor_api.py' in your project root.
2. Import the module in your main script.

--- CODE EXAMPLE ---

from sensor_api import ProximitySensor

# Initialize (Auto-detects port, High Speed Mode)
# trigger_dist_mm: Distance threshold (e.g., 800mm)
# dwell_time_sec: User must stay for X seconds to trigger
sensor = ProximitySensor(trigger_dist_mm=800, dwell_time_sec=2.0)

while True:
    # 1. CRITICAL: Update sensor state (Must be called every frame)
    sensor.update()

    # 2. Check Trigger (Event Switch)
    # Returns True only once when a user is confirmed
    if sensor.is_triggered:
        print("User Detected! Starting generation...")
        # YOUR_ART_FUNCTION_HERE()

    # 3. Get Real-time Data (Optional)
    # Returns integer distance in mm
    current_dist = sensor.distance
    
----------------------------------------------------------------
*Note*: 
- The sensor runs at approx. 100Hz polling rate.
- Ensure the "COM" port is used for stable connection.