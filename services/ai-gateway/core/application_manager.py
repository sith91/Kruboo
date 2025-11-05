# services/ai-gateway/core/application_manager.py
import os
import subprocess
import asyncio
import psutil
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import platform

class ApplicationManager:
    def __init__(self):
        self.running_apps = {}
        self.applications_config = {}
        self.is_initialized = False

    async def initialize(self):
        """Initialize application manager"""
        try:
            await self._load_applications_config()
            await self._scan_running_applications()
            self.is_initialized = True
            logging.info("Application Manager initialized successfully")
        except Exception as e:
            logging.error(f"Application Manager initialization failed: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        self.running_apps.clear()

    async def launch_application(self, app_name: str, arguments: List[str] = None) -> bool:
        """Launch an application by name"""
        try:
            app_config = self._get_application_config(app_name)
            if not app_config:
                logging.error(f"Application '{app_name}' not configured")
                return False

            # Build command
            command = [app_config['path']]
            if arguments:
                command.extend(arguments)

            # Launch application
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL
            )

            # Store process info
            self.running_apps[app_name] = {
                'process': process,
                'pid': process.pid,
                'start_time': asyncio.get_event_loop().time(),
                'arguments': arguments or []
            }

            logging.info(f"Application '{app_name}' launched with PID {process.pid}")
            return True

        except Exception as e:
            logging.error(f"Failed to launch application '{app_name}': {e}")
            return False

    async def close_application(self, app_name: str, force: bool = False) -> bool:
        """Close an application by name"""
        try:
            app_info = self.running_apps.get(app_name)
            if not app_info:
                # Try to find by process name
                return await self._close_application_by_process_name(app_name, force)

            process = app_info['process']
            
            if force:
                process.terminate()
            else:
                # Try graceful closure first
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    # Force kill if graceful fails
                    process.kill()
                    await process.wait()

            # Remove from running apps
            self.running_apps.pop(app_name, None)
            logging.info(f"Application '{app_name}' closed")
            return True

        except Exception as e:
            logging.error(f"Failed to close application '{app_name}': {e}")
            return False

    async def get_running_applications(self) -> List[Dict[str, Any]]:
        """Get list of running applications"""
        try:
            running_apps = []
            
            # Add applications launched by us
            for app_name, app_info in self.running_apps.items():
                running_apps.append({
                    'name': app_name,
                    'pid': app_info['pid'],
                    'status': 'running',
                    'managed': True,
                    'start_time': app_info['start_time']
                })

            # Add system-detected applications
            system_apps = await self._get_system_running_applications()
            running_apps.extend(system_apps)

            return running_apps

        except Exception as e:
            logging.error(f"Failed to get running applications: {e}")
            return []

    async def switch_to_application(self, app_name: str) -> bool:
        """Switch focus to an application (platform-specific)"""
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                return await self._switch_to_application_macos(app_name)
            elif system == "Windows":
                return await self._switch_to_application_windows(app_name)
            elif system == "Linux":
                return await self._switch_to_application_linux(app_name)
            else:
                logging.warning(f"Application switching not supported on {system}")
                return False

        except Exception as e:
            logging.error(f"Failed to switch to application '{app_name}': {e}")
            return False

    async def execute_application_command(self, app_name: str, command: str, parameters: Dict[str, Any] = None) -> bool:
        """Execute a command within an application"""
        try:
            app_config = self._get_application_config(app_name)
            if not app_config:
                return False

            # Map common commands to platform-specific actions
            if command == "save":
                return await self._send_save_command(app_name)
            elif command == "new":
                return await self._send_new_command(app_name)
            elif command == "close_tab":
                return await self._send_close_tab_command(app_name)
            else:
                logging.warning(f"Unknown application command: {command}")
                return False

        except Exception as e:
            logging.error(f"Failed to execute command '{command}' for '{app_name}': {e}")
            return False

    async def get_application_info(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Get information about an application"""
        app_config = self._get_application_config(app_name)
        if not app_config:
            return None

        # Check if application is running
        is_running = app_name in self.running_apps
        app_info = {
            'name': app_name,
            'configured': True,
            'running': is_running,
            'path': app_config['path'],
            'supported_commands': app_config.get('commands', [])
        }

        if is_running:
            app_info.update(self.running_apps[app_name])

        return app_info

    async def health_check(self) -> bool:
        """Health check for application manager"""
        return self.is_initialized

    # Private methods
    async def _load_applications_config(self):
        """Load applications configuration"""
        # Default applications configuration
        self.applications_config = {
            'chrome': {
                'name': 'Google Chrome',
                'path': self._get_chrome_path(),
                'process_name': 'Google Chrome',
                'commands': ['new_tab', 'close_tab', 'reload']
            },
            'vscode': {
                'name': 'Visual Studio Code',
                'path': self._get_vscode_path(),
                'process_name': 'Code',
                'commands': ['save', 'new_file', 'close_tab']
            },
            'slack': {
                'name': 'Slack',
                'path': self._get_slack_path(),
                'process_name': 'Slack',
                'commands': ['focus']
            },
            'photoshop': {
                'name': 'Adobe Photoshop',
                'path': self._get_photoshop_path(),
                'process_name': 'Photoshop',
                'commands': ['save', 'export']
            },
            'excel': {
                'name': 'Microsoft Excel',
                'path': self._get_excel_path(),
                'process_name': 'Excel',
                'commands': ['save', 'new_workbook']
            },
            'word': {
                'name': 'Microsoft Word',
                'path': self._get_word_path(),
                'process_name': 'Word',
                'commands': ['save', 'new_document']
            }
        }

    async def _scan_running_applications(self):
        """Scan for currently running applications"""
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                proc_name = proc.info['name'].lower()
                
                # Match against configured applications
                for app_id, app_config in self.applications_config.items():
                    if app_config['process_name'].lower() in proc_name:
                        self.running_apps[app_id] = {
                            'pid': proc.info['pid'],
                            'process': proc,
                            'start_time': proc.create_time(),
                            'managed': False
                        }
                        break
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def _get_application_config(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Get application configuration by name or alias"""
        # Direct match
        if app_name in self.applications_config:
            return self.applications_config[app_name]
        
        # Alias match
        app_aliases = {
            'browser': 'chrome',
            'code': 'vscode',
            'editor': 'vscode',
            'spreadsheet': 'excel',
            'document': 'word'
        }
        
        aliased_name = app_aliases.get(app_name.lower())
        if aliased_name and aliased_name in self.applications_config:
            return self.applications_config[aliased_name]
        
        return None

    async def _close_application_by_process_name(self, app_name: str, force: bool) -> bool:
        """Close application by process name"""
        app_config = self._get_application_config(app_name)
        if not app_config:
            return False

        process_name = app_config['process_name']
        closed_count = 0

        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return closed_count > 0

    async def _get_system_running_applications(self) -> List[Dict[str, Any]]:
        """Get applications running on the system"""
        system_apps = []
        
        for proc in psutil.process_iter(['name', 'pid', 'create_time']):
            try:
                # Filter out system processes
                if self._is_user_application(proc.info['name']):
                    system_apps.append({
                        'name': proc.info['name'],
                        'pid': proc.info['pid'],
                        'status': 'running',
                        'managed': False,
                        'start_time': proc.info['create_time']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return system_apps

    def _is_user_application(self, process_name: str) -> bool:
        """Check if a process is a user application"""
        system_processes = {
            'system', 'kernel', 'launchd', 'init', 'svchost', 'services',
            'runtime', 'coreservices', 'background'
        }
        
        process_lower = process_name.lower()
        return not any(sys_proc in process_lower for sys_proc in system_processes)

    # Platform-specific application switching
    async def _switch_to_application_macos(self, app_name: str) -> bool:
        """Switch to application on macOS"""
        try:
            app_config = self._get_application_config(app_name)
            if not app_config:
                return False

            # Use AppleScript to activate application
            script = f'''
            tell application "{app_config['name']}"
                activate
            end tell
            '''
            
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            return process.returncode == 0
            
        except Exception as e:
            logging.error(f"macOS application switching failed: {e}")
            return False

    async def _switch_to_application_windows(self, app_name: str) -> bool:
        """Switch to application on Windows"""
        try:
            # This would use Windows API calls
            # For now, return mock implementation
            logging.info(f"Windows application switching for {app_name}")
            return True
        except Exception as e:
            logging.error(f"Windows application switching failed: {e}")
            return False

    async def _switch_to_application_linux(self, app_name: str) -> bool:
        """Switch to application on Linux"""
        try:
            # This would use wmctrl or similar tools
            # For now, return mock implementation
            logging.info(f"Linux application switching for {app_name}")
            return True
        except Exception as e:
            logging.error(f"Linux application switching failed: {e}")
            return False

    # Application command implementations
    async def _send_save_command(self, app_name: str) -> bool:
        """Send save command to application"""
        system = platform.system()
        
        if system == "Darwin":
            # macOS: Cmd+S
            return await self._send_key_combination_macos(app_name, 's', command=True)
        else:
            # Windows/Linux: Ctrl+S
            return await self._send_key_combination_generic(app_name, 's', control=True)

    async def _send_new_command(self, app_name: str) -> bool:
        """Send new file/document command to application"""
        system = platform.system()
        
        if system == "Darwin":
            # macOS: Cmd+N
            return await self._send_key_combination_macos(app_name, 'n', command=True)
        else:
            # Windows/Linux: Ctrl+N
            return await self._send_key_combination_generic(app_name, 'n', control=True)

    async def _send_close_tab_command(self, app_name: str) -> bool:
        """Send close tab command to application"""
        system = platform.system()
        
        if system == "Darwin":
            # macOS: Cmd+W
            return await self._send_key_combination_macos(app_name, 'w', command=True)
        else:
            # Windows/Linux: Ctrl+W
            return await self._send_key_combination_generic(app_name, 'w', control=True)

    async def _send_key_combination_macos(self, app_name: str, key: str, command: bool = False) -> bool:
        """Send key combination on macOS"""
        try:
            app_config = self._get_application_config(app_name)
            if not app_config:
                return False

            modifier = "command down" if command else ""
            script = f'''
            tell application "System Events"
                tell process "{app_config['process_name']}"
                    keystroke "{key}" using {{{modifier}}}
                end tell
            end tell
            '''
            
            process = await asyncio.create_subprocess_exec(
                'osascript', '-e', script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.wait()
            return process.returncode == 0
            
        except Exception as e:
            logging.error(f"macOS key combination failed: {e}")
            return False

    async def _send_key_combination_generic(self, app_name: str, key: str, control: bool = False) -> bool:
        """Send key combination on Windows/Linux"""
        # This would use platform-specific automation libraries
        logging.info(f"Sending key combination to {app_name}: {'Ctrl+' if control else ''}{key}")
        return True

    # Application path detection
    def _get_chrome_path(self) -> str:
        """Get Chrome executable path"""
        system = platform.system()
        if system == "Darwin":
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif system == "Windows":
            return "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        else:
            return "/usr/bin/google-chrome"

    def _get_vscode_path(self) -> str:
        """Get VS Code executable path"""
        system = platform.system()
        if system == "Darwin":
            return "/Applications/Visual Studio Code.app/Contents/MacOS/Electron"
        elif system == "Windows":
            return "C:\\Users\\{}\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe"
        else:
            return "/usr/bin/code"

    def _get_slack_path(self) -> str:
        """Get Slack executable path"""
        system = platform.system()
        if system == "Darwin":
            return "/Applications/Slack.app/Contents/MacOS/Slack"
        elif system == "Windows":
            return "C:\\Users\\{}\\AppData\\Local\\slack\\slack.exe"
        else:
            return "/usr/bin/slack"

    def _get_photoshop_path(self) -> str:
        """Get Photoshop executable path"""
        system = platform.system()
        if system == "Darwin":
            return "/Applications/Adobe Photoshop 2023/Adobe Photoshop 2023.app/Contents/MacOS/Adobe Photoshop 2023"
        elif system == "Windows":
            return "C:\\Program Files\\Adobe\\Adobe Photoshop 2023\\Photoshop.exe"
        else:
            return ""

    def _get_excel_path(self) -> str:
        """Get Excel executable path"""
        system = platform.system()
        if system == "Darwin":
            return "/Applications/Microsoft Excel.app/Contents/MacOS/Microsoft Excel"
        elif system == "Windows":
            return "C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE"
        else:
            return ""

    def _get_word_path(self) -> str:
        """Get Word executable path"""
        system = platform.system()
        if system == "Darwin":
            return "/Applications/Microsoft Word.app/Contents/MacOS/Microsoft Word"
        elif system == "Windows":
            return "C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE"
        else:
            return ""
