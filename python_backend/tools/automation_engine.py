import time
import threading
import json
import platform
from datetime import datetime
import subprocess
import requests
from tools.memory_manager import MemoryManager
from agents.assistant import _gmail_plugin, _calendar_plugin
from tools.system_tools import get_weather, open_application, control_media

class AutomationEngine(threading.Thread):
    def __init__(self, broadcast_callback=None):
        super().__init__()
        self.memory = MemoryManager()
        self.broadcast_callback = broadcast_callback
        self.daemon = True
        self.running = True

    def run(self):
        print("Automation Engine Started...")
        while self.running:
            try:
                self.evaluate_rules()
            except Exception as e:
                print(f"Automation Engine Error: {e}")
            time.sleep(60) # Check every minute

    def _is_cooling_down(self, rule, default_cooldown_minutes=30):
        last_run = rule.get('last_run')
        if not last_run:
            return False
        try:
            from dateutil import parser
            last_run_dt = parser.parse(str(last_run)).replace(tzinfo=None)
            now_utc = datetime.utcnow()
            
            t_config = rule.get('trigger_config')
            if isinstance(t_config, str):
                try:
                    t_config = json.loads(t_config)
                except:
                    t_config = {}
            elif not isinstance(t_config, dict):
                t_config = {}
                
            cooldown_min = int(t_config.get('cooldown_minutes', default_cooldown_minutes))
            elapsed_seconds = (now_utc - last_run_dt).total_seconds()
            
            if elapsed_seconds < 0:
                return False
                
            return elapsed_seconds < (cooldown_min * 60)
        except Exception:
            return False

    def evaluate_rules(self):
        rules = self.memory.get_automations()
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        for rule in rules:
            if not rule.get('enabled', True): continue
            
            trigger_met = False
            t_type = rule.get('trigger_type')
            t_config = rule.get('trigger_config', {})
            if isinstance(t_config, str):
                try:
                    t_config = json.loads(t_config)
                except:
                    t_config = {}
            
            # 1. Time Trigger
            if t_type == "time":
                if t_config.get("time") == current_time:
                    # Check if already run today or within cooldown
                    last_run = rule.get('last_run')
                    if not last_run or last_run[:10] != now.strftime("%Y-%m-%d"):
                        if not self._is_cooling_down(rule, default_cooldown_minutes=720):
                            trigger_met = True
            
            # 2. Battery Level Trigger (Cooldown: 30m default)
            elif t_type == "battery":
                if not self._is_cooling_down(rule, default_cooldown_minutes=30):
                    try:
                        import psutil
                        battery = psutil.sensors_battery()
                        if battery:
                            percent = battery.percent
                            threshold = int(t_config.get("threshold", 20))
                            if percent <= threshold:
                                trigger_met = True
                        else:
                            # Fallback for systems where psutil fails
                            os_name = platform.system()
                            if os_name == "Darwin":
                                res = subprocess.check_output(["pmset", "-g", "batt"]).decode()
                                if "InternalBattery" in res:
                                    percent = int(res.split("\t")[1].split("%")[0])
                                    if percent <= int(t_config.get("threshold", 20)):
                                        trigger_met = True
                    except: pass

            # 3. Email Trigger (Cooldown: 15m default)
            elif t_type == "email":
                if not self._is_cooling_down(rule, default_cooldown_minutes=15):
                    try:
                        sender = t_config.get("sender", "").lower()
                        emails = _gmail_plugin.execute("check_emails", {"category": "UNREAD"})
                        if emails and isinstance(emails, list):
                            for email in emails:
                                if sender in str(email.get("from", "")).lower():
                                    trigger_met = True
                                    break
                    except: pass

            # 4. Weather Trigger (Cooldown: 60m default)
            elif t_type == "weather":
                if not self._is_cooling_down(rule, default_cooldown_minutes=60):
                    try:
                        condition = t_config.get("condition", "").lower() # e.g. "rain", "clear"
                        weather_data = get_weather("current location")
                        if condition in str(weather_data).lower():
                            trigger_met = True
                    except: pass

            # 5. Stock Price Trigger (Cooldown: 30m default)
            elif t_type == "stock":
                if not self._is_cooling_down(rule, default_cooldown_minutes=30):
                    try:
                        symbol = t_config.get("symbol", "").upper()
                        target_price = float(t_config.get("price", 0))
                        direction = t_config.get("direction", "above") # "above" or "below"
                        
                        # Using a free public API (Yahoo Finance via requests)
                        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                        headers = {'User-Agent': 'Mozilla/5.0'}
                        res = requests.get(url, headers=headers).json()
                        current_price = res['chart']['result'][0]['meta']['regularMarketPrice']
                        
                        if direction == "above" and current_price >= target_price:
                            trigger_met = True
                        elif direction == "below" and current_price <= target_price:
                            trigger_met = True
                    except: pass

            # 6. Calendar Meeting Reminder Trigger (Cooldown: 30m default)
            elif t_type == "calendar_reminder":
                if not self._is_cooling_down(rule, default_cooldown_minutes=30):
                    try:
                        events = _calendar_plugin.execute("list_events", {"limit": 1})
                        if events and isinstance(events, list):
                            event = events[0]
                            start_str = event['start'].get('dateTime', event['start'].get('date'))
                            # Parse ISO date
                            from dateutil import parser
                            start_time = parser.parse(start_str)
                            # Ensure timezone awareness if needed, but here we just compare
                            time_diff = (start_time.replace(tzinfo=None) - datetime.now()).total_seconds() / 60
                            
                            threshold = int(t_config.get("minutes", 5))
                            if 0 < time_diff <= threshold:
                                trigger_met = True
                    except: pass

            if trigger_met:
                self.execute_action(rule)

    def execute_action(self, rule):
        print(f"Executing Automation: {rule['name']}")
        a_type = rule['action_type']
        a_config = rule['action_config']
        
        try:
            if a_type == "open_app":
                open_application(a_config.get("app_name"))
            elif a_type == "media_control":
                control_media(a_config.get("command"))
            elif a_type == "notification":
                msg = a_config.get("message", "System Notification")
                print(f"NOTIFICATION: {msg}")
                os_name = platform.system()
                if os_name == "Darwin":
                    subprocess.run(['osascript', '-e', f'display notification "{msg}" with title "AI Assistant"'])
                elif os_name == "Windows":
                    # Simple Windows notification using msg command or similar
                    subprocess.run(['msg', '*', msg], capture_output=True)
                elif os_name == "Linux":
                    subprocess.run(['notify-send', 'AI Assistant', msg])
                
                if self.broadcast_callback:
                    self.broadcast_callback({"type": "notification", "content": msg})
            elif a_type == "close_app":
                from tools.system_tools import close_application
                close_application(a_config.get("app_name"))
            elif a_type == "voice_alert":
                msg = a_config.get("message", "Attention needed")
                os_name = platform.system()
                if os_name == "Darwin":
                    subprocess.run(['say', msg])
                elif os_name == "Windows":
                    # Windows PowerShell Speech
                    subprocess.run(['PowerShell', '-Command', f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{msg}")'])
                elif os_name == "Linux":
                    subprocess.run(['espeak', msg])
                    
                if self.broadcast_callback:
                    self.broadcast_callback({"type": "voice_alert", "content": msg})
            
            self.memory.update_automation_run_time(rule['id'])
        except Exception as e:
            print(f"Failed to execute action for {rule['name']}: {e}")

    def stop(self):
        self.running = False
