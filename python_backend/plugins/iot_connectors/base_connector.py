from abc import ABC, abstractmethod

class IoTConnector(ABC):
    @property
    @abstractmethod
    def vendor_id(self):
        """Unique ID for the vendor (e.g., 'philips_hue')."""
        pass

    @property
    @abstractmethod
    def display_name(self):
        """Human-readable name (e.g., 'Philips Hue')."""
        pass

    @property
    @abstractmethod
    def config_schema(self):
        """List of fields needed to activate the connector."""
        pass

    @abstractmethod
    def authenticate(self, config_data):
        """Test connection and return success status."""
        pass

    @abstractmethod
    def get_devices(self):
        """Returns a list of discovered devices for this vendor."""
        pass

    @abstractmethod
    def control(self, device_id, action, value=None):
        """Send command to a specific device."""
        pass
