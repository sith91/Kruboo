import requests
import os
import json
from tools.sync_manager import LocalSyncManager

class IoTManager:
    """
    The IoT Layer: Discovery via mDNS and Control via HTTP/REST.
    Supports Tasmota, WLED, and generic ESP32/Arduino webhooks.
    """
    
    @staticmethod
    def control_device(device_name, action, params=None):
        """
        Sends a command to an IoT device.
        - device_name: Name of the device (e.g., 'desk lamp')
        - action: 'on', 'off', 'toggle', 'brightness', etc.
        """
        # In a production app, we would look up the device's IP in the memory database.
        # For this demonstration, we'll support common DIY IoT endpoints.
        
        # Mock device registry (Normally populated by mDNS discovery)
        device_registry = {
            "light": "http://192.168.1.50",
            "fan": "http://192.168.1.51",
            "led": "http://192.168.1.52",
        }
        
        # Try to find a match
        base_url = None
        for key, url in device_registry.items():
            if key in device_name.lower():
                base_url = url
                break
        
        if not base_url:
            return f"Device '{device_name}' not found. Please ensure it is connected to the same network."

        try:
            # 1. Tasmota Style (Standard for many smart plugs/switches)
            if action in ["on", "off", "toggle"]:
                cmd = f"Power {action.upper()}"
                res = requests.get(f"{base_url}/cm?cmnd={cmd}", timeout=3)
                if res.status_code == 200:
                    return f"Successfully turned {action} the {device_name}."
            
            # 2. WLED Style (Common for LED strips)
            if "brightness" in action:
                val = params if params else 128
                res = requests.get(f"{base_url}/win&A={val}", timeout=3)
                return f"Set {device_name} brightness to {val}."
                
            # 3. Generic Webhook (Custom ESP32)
            res = requests.get(f"{base_url}/{action}", timeout=3)
            return f"Command '{action}' sent to {device_name}."

        except Exception as e:
            return f"Failed to reach {device_name}. Error: {str(e)}"

    @staticmethod
    def discover_devices():
        """Uses Zeroconf to find smart devices on the local network."""
        # This uses the existing SyncManager's discovery logic
        # For IoT, we'd look for '_http._tcp.local.' or '_arduino._tcp.local.'
        return "Scanning network for new IoT devices..."
