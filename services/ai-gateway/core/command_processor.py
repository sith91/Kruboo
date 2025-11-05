from typing import Dict, Any
import logging
from dataclasses import dataclass

@dataclass
class CommandResult:
    response: str
    confidence: float
    data: Any = None

class CommandProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.command_handlers = self._initialize_handlers()

    async def execute(self, command: str, parameters: Dict[str, Any] = None) -> CommandResult:
        """Execute a system command"""
        command_lower = command.lower()
        parameters = parameters or {}

        # Find appropriate handler
        for handler in self.command_handlers:
            if any(keyword in command_lower for keyword in handler['keywords']):
                return await handler['handler'](command, parameters)

        # No handler found
        return CommandResult(
            response=f"I don't know how to handle: {command}",
            confidence=0.1
        )

    def _initialize_handlers(self) -> List[Dict]:
        """Initialize command handlers"""
        return [
            {
                'keywords': ['open', 'launch', 'start'],
                'handler': self._handle_open_app
            },
            {
                'keywords': ['close', 'quit', 'exit'],
                'handler': self._handle_close_app
            },
            {
                'keywords': ['search', 'find', 'look up'],
                'handler': self._handle_search
            },
            {
                'keywords': ['time', 'date'],
                'handler': self._handle_time_date
            },
            # Add more handlers as needed
        ]

    async def _handle_open_app(self, command: str, parameters: Dict[str, Any]) -> CommandResult:
        app_name = self._extract_app_name(command)
        return CommandResult(
            response=f"Opening {app_name}",
            confidence=0.9,
            data={'action': 'open_app', 'app_name': app_name}
        )

    async def _handle_close_app(self, command: str, parameters: Dict[str, Any]) -> CommandResult:
        app_name = self._extract_app_name(command)
        return CommandResult(
            response=f"Closing {app_name}",
            confidence=0.9,
            data={'action': 'close_app', 'app_name': app_name}
        )

    async def _handle_search(self, command: str, parameters: Dict[str, Any]) -> CommandResult:
        query = self._extract_search_query(command)
        return CommandResult(
            response=f"Searching for: {query}",
            confidence=0.9,
            data={'action': 'web_search', 'query': query}
        )

    async def _handle_time_date(self, command: str, parameters: Dict[str, Any]) -> CommandResult:
        from datetime import datetime
        now = datetime.now()
        if 'time' in command.lower():
            response = f"The current time is {now.strftime('%H:%M')}"
        else:
            response = f"Today's date is {now.strftime('%B %d, %Y')}"
        
        return CommandResult(
            response=response,
            confidence=1.0,
            data={'time': now.isoformat()}
        )

    def _extract_app_name(self, command: str) -> str:
        """Extract application name from command"""
        words = command.lower().split()
        stop_words = ['open', 'launch', 'start', 'close', 'quit', 'exit']
        app_words = [word for word in words if word not in stop_words]
        return ' '.join(app_words).title()

    def _extract_search_query(self, command: str) -> str:
        """Extract search query from command"""
        words = command.lower().split()
        stop_words = ['search', 'for', 'find', 'look', 'up', 'google']
        query_words = [word for word in words if word not in stop_words]
        return ' '.join(query_words)
