from abc import ABC, abstractmethod

class BasePlugin(ABC):
    """
    The base contract for all Antigravity integrations.
    Every new platform (Gmail, Zoho, etc.) must implement these methods.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The human-readable name of the plugin."""
        pass

    @abstractmethod
    def execute(self, action: str, params: dict) -> str:
        """
        The main entry point for the AI to interact with the plugin.
        Example: execute('send_message', {'to': 'John', 'body': 'Hello'})
        """
        pass

    def get_capabilities(self) -> list[str]:
        """Returns a list of things this plugin can do."""
        return []
