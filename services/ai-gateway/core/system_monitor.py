# services/ai-gateway/core/system_monitor.py
import asyncio
import psutil
import platform
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int  # in bytes
    status: str
    create_time: float
    command: str

@dataclass
class SystemMetrics:
    cpu_usage: float
    memory_usage: float
    memory_total: int
    memory_available: int
    disk_usage: float
    disk_total: int
    disk_free: int
    boot_time: float
    uptime: float

class SystemMonitor:
    def __init__(self):
        self.monitoring = False
        self.monitoring_interval = 5  # seconds
        self.monitoring_task = None
        self.metrics_history = []
        self.max_history_size = 100
        self.alert_rules = []
        self.is_initialized = False

    async def initialize(self):
        """Initialize system monitor"""
        try:
            # Validate we can access system metrics
            await self._validate_system_access()
            self.is_initialized = True
            logging.info("System Monitor initialized successfully")
        except Exception as e:
            logging.error(f"System Monitor initialization failed: {e}")
            raise

    async def start_monitoring(self, interval: int = 5):
        """Start continuous system monitoring"""
        if self.monitoring:
            logging.warning("System monitoring is already running")
            return

        self.monitoring_interval = interval
        self.monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logging.info(f"System monitoring started with {interval}s interval")

    async def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logging.info("System monitoring stopped")

    async def get_cpu_usage(self) -> Dict[str, Any]:
        """Get detailed CPU usage information"""
        try:
            # Get per-core usage
            per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            total_cpu = psutil.cpu_percent(interval=0.1)
            
            # Get CPU times
            cpu_times = psutil.cpu_times()
            
            # Get CPU frequency
            try:
                cpu_freq = psutil.cpu_freq()
                current_freq = cpu_freq.current if cpu_freq else None
                max_freq = cpu_freq.max if cpu_freq else None
            except:
                current_freq = None
                max_freq = None
            
            # Get load average (Unix-like systems)
            load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
            
            return {
                'total_usage': total_cpu,
                'per_core_usage': per_cpu,
                'core_count': len(per_cpu),
                'user_time': cpu_times.user,
                'system_time': cpu_times.system,
                'idle_time': cpu_times.idle,
                'current_frequency': current_freq,
                'max_frequency': max_freq,
                'load_1min': load_avg[0],
                'load_5min': load_avg[1],
                'load_15min': load_avg[2],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Failed to get CPU usage: {e}")
            raise

    async def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total': memory.total,
                'available': memory.available,
                'used': memory.used,
                'percent': memory.percent,
                'free': memory.free,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_free': swap.free,
                'swap_percent': swap.percent,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Failed to get memory usage: {e}")
            raise

    async def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            disk = psutil.disk_usage(path)
            disk_io = psutil.disk_io_counters()
            
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0,
                'read_count': disk_io.read_count if disk_io else 0,
                'write_count': disk_io.write_count if disk_io else 0,
                'path': path,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Failed to get disk usage: {e}")
            raise

    async def get_running_processes(self, limit: int = 50) -> List[ProcessInfo]:
        """Get list of running processes with resource usage"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                           'memory_info', 'status', 'create_time', 'cmdline']):
                try:
                    # Limit the number of processes we return
                    if len(processes) >= limit:
                        break
                    
                    # Get process info
                    cpu_percent = proc.info['cpu_percent'] or 0
                    memory_percent = proc.info['memory_percent'] or 0
                    memory_rss = proc.info['memory_info'].rss if proc.info['memory_info'] else 0
                    command = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else proc.info['name']
                    
                    process_info = ProcessInfo(
                        pid=proc.info['pid'],
                        name=proc.info['name'],
                        cpu_percent=cpu_percent,
                        memory_percent=memory_percent,
                        memory_rss=memory_rss,
                        status=proc.info['status'],
                        create_time=proc.info['create_time'],
                        command=command[:100]  # Limit command length
                    )
                    
                    processes.append(process_info)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Sort by CPU usage (descending)
            processes.sort(key=lambda p: p.cpu_percent, reverse=True)
            
            return processes
            
        except Exception as e:
            logging.error(f"Failed to get running processes: {e}")
            raise

    async def kill_process(self, pid: int) -> bool:
        """Kill a process by PID"""
        try:
            process = psutil.Process(pid)
            process.terminate()  # Graceful termination
            
            # Wait for process to terminate
            try:
                process.wait(timeout=5)
                logging.info(f"Process {pid} terminated successfully")
                return True
            except psutil.TimeoutExpired:
                # Force kill if graceful termination fails
                process.kill()
                logging.warning(f"Process {pid} force killed")
                return True
                
        except psutil.NoSuchProcess:
            logging.error(f"Process {pid} does not exist")
            return False
        except psutil.AccessDenied:
            logging.error(f"Access denied to kill process {pid}")
            return False
        except Exception as e:
            logging.error(f"Failed to kill process {pid}: {e}")
            return False

    async def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            # CPU information
            cpu_info = await self.get_cpu_usage()
            
            # Memory information
            memory_info = await self.get_memory_usage()
            
            # Disk information
            disk_info = await self.get_disk_usage()
            
            # Network information
            network_info = await self._get_network_info()
            
            # System information
            boot_time = psutil.boot_time()
            uptime = datetime.now().timestamp() - boot_time
            
            return {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor()
                },
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'network': network_info,
                'boot_time': boot_time,
                'uptime': uptime,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Failed to get system info: {e}")
            raise

    async def get_metrics_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get historical system metrics"""
        return self.metrics_history[-limit:]

    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        return self.monitoring

    async def health_check(self) -> bool:
        """Health check for system monitor"""
        try:
            # Quick test of basic system metrics
            await self.get_cpu_usage()
            await self.get_memory_usage()
            return self.is_initialized
        except Exception as e:
            logging.error(f"System monitor health check failed: {e}")
            return False

    # Private methods
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Collect metrics
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Keep history size limited
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history.pop(0)
                
                # Check alert rules
                await self._check_alert_rules(metrics)
                
                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.monitoring_interval)

    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect all system metrics for history"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'cpu': await self.get_cpu_usage(),
            'memory': await self.get_memory_usage(),
            'disk': await self.get_disk_usage(),
            'process_count': len(await self.get_running_processes(limit=1000))
        }

    async def _get_network_info(self) -> Dict[str, Any]:
        """Get network interface information"""
        try:
            net_io = psutil.net_io_counters()
            net_connections = psutil.net_connections()
            
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'active_connections': len(net_connections),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logging.warning(f"Failed to get network info: {e}")
            return {}

    async def _check_alert_rules(self, metrics: Dict[str, Any]):
        """Check metrics against alert rules"""
        for rule in self.alert_rules:
            try:
                if await self._evaluate_alert_rule(rule, metrics):
                    await self._trigger_alert(rule, metrics)
            except Exception as e:
                logging.error(f"Alert rule evaluation failed: {e}")

    async def _evaluate_alert_rule(self, rule: Dict, metrics: Dict) -> bool:
        """Evaluate a single alert rule"""
        # Simple threshold-based rules
        metric_value = self._get_metric_value(metrics, rule['metric'])
        threshold = rule['threshold']
        
        if rule['condition'] == 'gt':
            return metric_value > threshold
        elif rule['condition'] == 'lt':
            return metric_value < threshold
        elif rule['condition'] == 'eq':
            return metric_value == threshold
        
        return False

    def _get_metric_value(self, metrics: Dict, metric_path: str) -> float:
        """Get metric value from nested dictionary using dot notation"""
        keys = metric_path.split('.')
        value = metrics
        for key in keys:
            value = value.get(key, {})
        return float(value) if value else 0.0

    async def _trigger_alert(self, rule: Dict, metrics: Dict):
        """Trigger an alert"""
        logging.warning(f"ALERT: {rule['name']} - {rule['metric']} {rule['condition']} {rule['threshold']}")
        # In production, this would send notifications, emails, etc.

    async def _validate_system_access(self):
        """Validate that we can access system metrics"""
        try:
            # Test basic metric access
            psutil.cpu_percent(interval=0.1)
            psutil.virtual_memory()
            psutil.disk_usage('/')
            psutil.process_iter()
        except Exception as e:
            raise RuntimeError(f"System access validation failed: {e}")
