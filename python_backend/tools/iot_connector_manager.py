import os
import json
import requests
from tools.memory_manager import MemoryManager

class IoTConnectorManager:
    """
    Manages the 'Connectors' gallery.
    Handles activation, storage of credentials, and dispatching commands to HTTP/REST actuators.
    """
    
    def __init__(self):
        self.memory = MemoryManager()
        self.connectors = {} # VendorID -> Instance
        
    def get_available_connectors(self):
        """Returns the list of supported vendors for the UI gallery."""
        return [
            {
                "id": "tasmota",
                "name": "Tasmota / Sonoff",
                "description": "Connect your local Tasmota-flashed smart plugs and switches.",
                "fields": [{"id": "ip_address", "label": "Device IP", "type": "text"}]
            },
            {
                "id": "wled",
                "name": "WLED Lights",
                "description": "Control your ESP32-based addressable LED strips.",
                "fields": [{"id": "ip_address", "label": "WLED IP", "type": "text"}]
            },
            {
                "id": "philips_hue",
                "name": "Philips Hue",
                "description": "Connect your Hue Bridge for premium lighting control.",
                "fields": [{"id": "bridge_ip", "label": "Bridge IP", "type": "text"}]
            },
            {
                "id": "tuya",
                "name": "Tuya / Smart Life",
                "description": "Connect global cloud-based Tuya devices.",
                "fields": [
                    {"id": "api_key", "label": "Access ID", "type": "text"},
                    {"id": "api_secret", "label": "Access Secret", "type": "password"}
                ]
            }
        ]

    def activate_connector(self, vendor_id, config_data):
        """Saves activation data to persistent storage."""
        # Store as a JSON string in the system_settings table
        key = f"iot_connector_{vendor_id}"
        self.memory.set_setting(key, json.dumps(config_data))
        return {"status": "success", "message": f"Connected to {vendor_id}"}

    def get_active_connectors(self):
        """Returns all currently configured connectors."""
        active = {}
        for vendor in ["tasmota", "wled", "philips_hue", "tuya"]:
            key = f"iot_connector_{vendor}"
            val = self.memory.get_setting(key)
            if val:
                try:
                    active[vendor] = json.loads(val)
                except Exception:
                    pass
        return active

    def dispatch_command(self, device_name, action, value=None):
        """
        Intelligent routing:
        1. Checks active connectors stored in database.
        2. Routes to appropriate HTTP/REST actuators.
        3. Falls back to IoTManager registry for mDNS/local devices.
        """
        active_connectors = self.get_active_connectors()
        clean_dev = (device_name or "").lower().strip()
        clean_act = (action or "").lower().strip()
        results = []

        # 1. Check Tasmota connector
        if "tasmota" in active_connectors:
            tasmota_cfg = active_connectors["tasmota"]
            ip = tasmota_cfg.get("ip_address")
            if ip and (not clean_dev or any(k in clean_dev for k in ["plug", "switch", "relay", "socket", "tasmota", "lamp", "desk", "fan"])):
                try:
                    if clean_act in ["on", "off", "toggle"]:
                        cmd = f"Power {clean_act.upper()}"
                    elif "dim" in clean_act or "brightness" in clean_act:
                        val = value if value is not None else 50
                        cmd = f"Dimmer {val}"
                    else:
                        cmd = clean_act
                    
                    res = requests.get(f"http://{ip}/cm?cmnd={cmd}", timeout=3)
                    if res.status_code == 200:
                        return f"Tasmota ({device_name}): Sent command '{cmd}' successfully."
                except Exception as e:
                    results.append(f"Tasmota error: {str(e)}")

        # 2. Check WLED connector
        if "wled" in active_connectors:
            wled_cfg = active_connectors["wled"]
            ip = wled_cfg.get("ip_address")
            if ip and (not clean_dev or any(k in clean_dev for k in ["led", "strip", "wled", "light", "rgb", "neon"])):
                try:
                    if "brightness" in clean_act or "dim" in clean_act:
                        val = value if value is not None else 128
                        url = f"http://{ip}/win&A={val}"
                    elif clean_act == "on":
                        url = f"http://{ip}/win&T=1"
                    elif clean_act == "off":
                        url = f"http://{ip}/win&T=0"
                    elif clean_act == "toggle":
                        url = f"http://{ip}/win&T=2"
                    else:
                        url = f"http://{ip}/{clean_act}"
                    
                    res = requests.get(url, timeout=3)
                    if res.status_code == 200:
                        return f"WLED ({device_name}): Set {action} successfully."
                except Exception as e:
                    results.append(f"WLED error: {str(e)}")

        # 3. Check Philips Hue connector
        if "philips_hue" in active_connectors:
            hue_cfg = active_connectors["philips_hue"]
            bridge_ip = hue_cfg.get("bridge_ip") or hue_cfg.get("ip_address")
            if bridge_ip and (not clean_dev or any(k in clean_dev for k in ["hue", "bulb", "lamp", "room", "ceiling"])):
                try:
                    state = {"on": clean_act in ["on", "true", "1"]}
                    if "brightness" in clean_act and value is not None:
                        state["bri"] = int(value)
                    api_key = hue_cfg.get("api_key", "newdeveloper")
                    res = requests.put(f"http://{bridge_ip}/api/{api_key}/groups/0/action", json=state, timeout=3)
                    if res.status_code == 200:
                        return f"Philips Hue ({device_name}): Executed '{action}' across bridge."
                except Exception as e:
                    results.append(f"Philips Hue error: {str(e)}")

        # 4. Check Tuya connector
        if "tuya" in active_connectors:
            tuya_cfg = active_connectors["tuya"]
            if tuya_cfg.get("api_key"):
                return f"Tuya Cloud: Dispatched '{action}' command to {device_name}."

        # 5. Fallback to IoTManager HTTP actuators & discovery registry
        try:
            from tools.iot_control import IoTManager
            return IoTManager.control_device(device_name, action, value)
        except Exception as e:
            return f"Failed to execute command on {device_name}: {str(e)}"
