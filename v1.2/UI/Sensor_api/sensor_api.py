import serial
import serial.tools.list_ports
import time, logging

class ProximitySensor:
    def __init__(self, port=None, baudrate=115200, trigger_dist_mm=800, dwell_time_sec=2.0, cooldown_sec=3.0):
        """
        Hardware Interface for VL53L0X Laser Ranging Sensor.
        Version: V2.0 - Ultra Low Latency Mode (100Hz Capable)
        
        Features:
        - Auto-discovery of CH340/CP210x drivers
        - Anti-lag buffer flushing for real-time responsiveness
        - Built-in dwell time and cooldown logic
        
        Args:
            trigger_dist_mm (int): Threshold distance to trigger activation.
            dwell_time_sec (float): Duration user must stay within range to trigger.
            cooldown_sec (float): Reset period after activation.
        """
        self.trigger_dist = trigger_dist_mm
        self.dwell_time = dwell_time_sec
        self.cooldown = cooldown_sec
        
        self._ser = None
        self._last_trigger_timestamp = 0
        self._detection_start_timestamp = None
        self._current_distance = 9999 
        self._trigger_state = False
        
        self._connect(port, baudrate)

    def _connect(self, specific_port, baudrate):
        """Internal method to establish serial connection with auto-discovery."""
        target_port = specific_port
        
        # Auto-discovery if no port specified
        if target_port is None:
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                # Auto-detect common USB-Serial chips (CH340, CP210x, etc.)
                if any(x in p.description for x in ["CH340", "CP210", "USB Serial"]):
                    target_port = p.device
                    break
        
        if target_port:
            try:
                # Optimize connection for low latency (timeout=0 for non-blocking read)
                self._ser = serial.Serial(target_port, baudrate, timeout=0, write_timeout=0)
                time.sleep(2) # Allow MCU to reboot after connection
                
                # Flush any stale data from the hardware buffer
                self._ser.reset_input_buffer()
                logging.info(f"[System] Hardware connected on {target_port} (High Speed Mode)")
            except Exception as e:
                logging.warning(f"[Error] Connection failed: {e}")
        else:
            logging.warning("[Error] No sensor hardware found. Please check USB drivers.")

    def update(self):
        """
        CRITICAL: Must be called in the main application loop.
        Reads the serial buffer using an anti-lag strategy (drains buffer completely)
        to ensure the latest data is used.
        """
        self._trigger_state = False 
        
        if not self._ser:
            return

        # --- V2.0 ANTI-LAG ALGORITHM ---
        # Loop until we have processed ALL currently available bytes
        # and only use the VERY LAST complete reading for logic.
        latest_valid_dist = None
        
        if self._ser.in_waiting > 0:
            try:
                # Read entire buffer at once
                raw_data = self._ser.read(self._ser.in_waiting).decode('utf-8', errors='ignore')
                lines = raw_data.split('\n')
                
                # Iterate backwards to find the most recent valid reading
                for line in reversed(lines):
                    line = line.strip()
                    if line.isdigit():
                        latest_valid_dist = int(line)
                        break 
            except Exception:
                pass
        
        # Only process if we obtained new data this frame
        if latest_valid_dist is not None:
            dist = latest_valid_dist
            
            # Filter hardware error codes (e.g. 8888 means out of range)
            if dist > 8000:
                self._detection_start_timestamp = None
                self._current_distance = 9999
                return

            self._current_distance = dist
            
            # --- Logic: Trigger Detection ---
            if dist < self.trigger_dist:
                if self._detection_start_timestamp is None:
                    self._detection_start_timestamp = time.time()
                else:
                    duration = time.time() - self._detection_start_timestamp
                    # Check dwell time requirement
                    if duration >= self.dwell_time:
                        # Check cooldown requirement
                        if time.time() - self._last_trigger_timestamp > self.cooldown:
                            self._last_trigger_timestamp = time.time()
                            self._detection_start_timestamp = None
                            self._trigger_state = True # FIRE TRIGGER
            else:
                self._detection_start_timestamp = None

    @property
    def distance(self):
        """Real-time distance in millimeters (int)."""
        return self._current_distance

    @property
    def is_triggered(self):
        """Returns True ONLY in the exact frame the user triggers the interaction."""
        return self._trigger_state

# --- Integration Test (Run this file directly to verify) ---
if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logging.info("Initializing Hardware (Zero Latency Mode)...")
    sensor = ProximitySensor(trigger_dist_mm=400, dwell_time_sec=1.5)
    logging.info("Hardware Ready. Try moving your hand fast!")
    
    try:
        while True:
            sensor.update()
            logging.debug(f"Dist: {sensor.distance} mm")
            if sensor.distance < 400:
                logging.info(f"Sensor Positive Feedback")
            else:
                logging.info(f"Sensor Negative Feedback")
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        logging.info("\nTerminated.")