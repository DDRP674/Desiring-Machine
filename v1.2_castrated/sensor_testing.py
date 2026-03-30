import time
import UI.Sensor_api.sensor_api as sa

print("Initializing Hardware (Zero Latency Mode)...")
sensor = sa.ProximitySensor(trigger_dist_mm=400, dwell_time_sec=1.5)
print("Hardware Ready. Try moving your hand fast!")

try:
    while True:
        sensor.update()
        print(f"Dist: {sensor.distance} mm")
        if sensor.distance < 400:
            print(f"Sensor Positive Feedback")
        else:
            print(f"Sensor Negative Feedback")
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print("\nTerminated.")