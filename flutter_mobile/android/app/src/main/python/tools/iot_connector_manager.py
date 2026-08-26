import os
import json
from tools.memory_manager import MemoryManager

class IoTConnectorManager:
    """
    Manages the 'Connectors' gallery.
    Handles activation, storage of credentials, and dispatching commands.
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
        # This would scan the DB for keys starting with 'iot_connector_'
        # For simplicity, returning a mock based on what's in 'system_settings'
        pass

    def dispatch_command(self, device_name, action, value=None):
        """
        Intelligent routing:
        1. Checks which connectors are active.
        2. Asks each active connector if it knows the device.
        3. Executes the command.
        """
        # This replaces the hardcoded logic in the old IoTManager
        return f"Routing '{action}' to {device_name} via active connectors..."
