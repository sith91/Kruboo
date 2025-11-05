# services/ai-gateway/core/command_processor.py
import asyncio
import subprocess
import shutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

class CommandProcessor:
    def __init__(self):
        self.command_registry = {}
        self.is_initialized = False

    async def initialize(self):
        """Initialize command processor"""
        try:
            await self._build_command_registry()
            self.is_initialized = True
            logging.info("Command Processor initialized successfully")
        except Exception as e:
            logging.error(f"Command Processor initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        self.command_registry.clear()

    async def execute(self, command: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a system command"""
        try:
            parameters = parameters or {}
            
            # Parse command and route to appropriate handler
            command_lower = command.lower().strip()
            
            if command_lower.startswith(('open ', 'launch ', 'start ')):
                return await self._handle_application_launch(command_lower, parameters)
            elif command_lower.startswith(('close ', 'quit ', 'exit ')):
                return await self._handle_application_close(command_lower, parameters)
            elif any(keyword in command_lower for keyword in ['search', 'find', 'locate']):
                return await self._handle_file_search(command_lower, parameters)
            elif any(keyword in command_lower for keyword in ['copy', 'move', 'delete', 'backup']):
                return await self._handle_file_operation(command_lower, parameters)
            elif any(keyword in command_lower for keyword in ['what time', 'what date']):
                return await self._handle_system_info(command_lower, parameters)
            else:
                return await self._handle_generic_command(command, parameters)
                
        except Exception as e:
            logging.error(f"Command execution failed: {e}")
            return {
                'success': False,
                'response': f"Command failed: {str(e)}",
                'confidence': 0.0,
                'execution_time': 0
            }

    async def get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        try:
            import platform
            import psutil
            
            boot_time = psutil.boot_time()
            uptime = datetime.now().timestamp() - boot_time
            
            return {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'architecture': platform.architecture()[0],
                'processor': platform.processor(),
                'boot_time': boot_time,
                'uptime': uptime,
                'current_time': datetime.now().isoformat(),
                'user': platform.node()
            }
            
        except Exception as e:
            logging.error(f"Failed to get system info: {e}")
            return {'error': str(e)}

    async def health_check(self) -> bool:
        """Health check for command processor"""
        return self.is_initialized

    # Command handlers
    async def _handle_application_launch(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle application launch commands"""
        try:
            # Extract application name from command
            app_name = self._extract_app_name(command)
            if not app_name:
                return {
                    'success': False,
                    'response': "Could not determine which application to launch",
                    'confidence': 0.3,
                    'execution_time': 0
                }

            # This would integrate with ApplicationManager
            # For now, return mock response
            return {
                'success': True,
                'response': f"Launching {app_name}",
                'confidence': 0.9,
                'execution_time': 0.1,
                'application': app_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'response': f"Failed to launch application: {str(e)}",
                'confidence': 0.0,
                'execution_time': 0
            }

    async def _handle_application_close(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle application close commands"""
        try:
            app_name = self._extract_app_name(command)
            if not app_name:
                return {
                    'success': False,
                    'response': "Could not determine which application to close",
                    'confidence': 0.3,
                    'execution_time': 0
                }

            # This would integrate with ApplicationManager
            return {
                'success': True,
                'response': f"Closing {app_name}",
                'confidence': 0.9,
                'execution_time': 0.1,
                'application': app_name
            }
            
        except Exception as e:
            return {
                'success': False,
                'response': f"Failed to close application: {str(e)}",
                'confidence': 0.0,
                'execution_time': 0
            }

    async def _handle_file_search(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file search commands"""
        try:
            search_query = self._extract_search_query(command)
            if not search_query:
                return {
                    'success': False,
                    'response': "What would you like me to search for?",
                    'confidence': 0.5,
                    'execution_time': 0
                }

            # This would integrate with FileSystemController
            return {
                'success': True,
                'response': f"Searching for files matching '{search_query}'",
                'confidence': 0.8,
                'execution_time': 0.2,
                'search_query': search_query
            }
            
        except Exception as e:
            return {
                'success': False,
                'response': f"Search failed: {str(e)}",
                'confidence': 0.0,
                'execution_time': 0
            }

    async def _handle_file_operation(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file operations"""
        try:
            operation = self._extract_file_operation(command)
            if not operation:
                return {
                    'success': False,
                    'response': "What file operation would you like to perform?",
                    'confidence': 0.4,
                    'execution_time': 0
                }

            return {
                'success': True,
                'response': f"Performing file operation: {operation}",
                'confidence': 0.8,
                'execution_time': 0.1,
                'operation': operation
            }
            
        except Exception as e:
            return {
                'success': False,
                'response': f"File operation failed: {str(e)}",
                'confidence': 0.0,
                'execution_time': 0
            }

    async def _handle_system_info(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system information queries"""
        try:
            if 'time' in command:
                current_time = datetime.now().strftime("%I:%M %p")
                return {
                    'success': True,
                    'response': f"The current time is {current_time}",
                    'confidence': 1.0,
                    'execution_time': 0.1
                }
            elif 'date' in command:
                current_date = datetime.now().strftime("%A, %B %d, %Y")
                return {
                    'success': True,
                    'response': f"Today is {current_date}",
                    'confidence': 1.0,
                    'execution_time': 0.1
                }
            else:
                return {
                    'success': False,
                    'response': "I can tell you the current time or date",
                    'confidence': 0.7,
                    'execution_time': 0
                }
                
        except Exception as e:
            return {
                'success': False,
                'response': f"Failed to get system information: {str(e)}",
                'confidence': 0.0,
                'execution_time': 0
            }

    async def _handle_generic_command(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generic commands"""
        try:
            # Try to execute as shell command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                response = stdout.decode().strip() or "Command executed successfully"
                return {
                    'success': True,
                    'response': response,
                    'confidence': 0.8,
                    'execution_time': 0.5
                }
            else:
                error_msg = stderr.decode().strip() or "Command failed"
                return {
                    'success': False,
                    'response': error_msg,
                    'confidence': 0.6,
                    'execution_time': 0.5
                }
                
        except Exception as e:
            return {
                'success': False,
                'response': f"Command execution error: {str(e)}",
                'confidence': 0.0,
                'execution_time': 0
            }

    # Helper methods
    def _extract_app_name(self, command: str) -> Optional[str]:
        """Extract application name from command"""
        prefixes = ['open ', 'launch ', 'start ', 'close ', 'quit ', 'exit ']
        
        for prefix in prefixes:
            if command.startswith(prefix):
                app_name = command[len(prefix):].strip()
                # Remove any trailing punctuation or common words
                app_name = app_name.rstrip('.,!?')
                app_name = app_name.replace(' the ', ' ').replace(' my ', ' ').strip()
                return app_name if app_name else None
        
        return None

    def _extract_search_query(self, command: str) -> Optional[str]:
        """Extract search query from command"""
        prefixes = ['search for ', 'find ', 'locate ', 'look for ']
        
        for prefix in prefixes:
            if command.startswith(prefix):
                query = command[len(prefix):].strip()
                # Remove common trailing phrases
                query = query.replace(' files', '').replace(' documents', '').strip()
                return query if query else None
        
        # Fallback: look for "search" or "find" in the command
        if 'search' in command or 'find' in command:
            # Extract words after search/find
            words = command.split()
            try:
                search_index = max(command.find('search'), command.find('find'))
                if search_index != -1:
                    query_words = []
                    for word in words[words.index('search' if 'search' in words else 'find') + 1:]:
                        if word in ['for', 'my', 'the']:
                            continue
                        query_words.append(word)
                    return ' '.join(query_words) if query_words else None
            except:
                pass
        
        return None

    def _extract_file_operation(self, command: str) -> Optional[str]:
        """Extract file operation from command"""
        operations = {
            'copy': ['copy', 'duplicate'],
            'move': ['move', 'transfer'],
            'delete': ['delete', 'remove', 'trash'],
            'backup': ['backup', 'save copy']
        }
        
        for operation, keywords in operations.items():
            if any(keyword in command for keyword in keywords):
                return operation
        
        return None

    async def _build_command_registry(self):
        """Build registry of supported commands"""
        self.command_registry = {
            'application_launch': {
                'keywords': ['open', 'launch', 'start'],
                'description': 'Launch applications',
                'examples': ['open chrome', 'launch photoshop', 'start excel']
            },
            'application_close': {
                'keywords': ['close', 'quit', 'exit'],
                'description': 'Close applications', 
                'examples': ['close browser', 'quit slack', 'exit word']
            },
            'file_search': {
                'keywords': ['search', 'find', 'locate'],
                'description': 'Search for files',
                'examples': ['find my documents', 'search for pdf files', 'locate budget spreadsheet']
            },
            'file_operations': {
                'keywords': ['copy', 'move', 'delete', 'backup'],
                'description': 'File operations',
                'examples': ['copy this file', 'move to backup', 'delete old files']
            },
            'system_info': {
                'keywords': ['time', 'date', 'what is'],
                'description': 'System information',
                'examples': ['what time is it', 'what is the date', 'current time']
            }
        }
