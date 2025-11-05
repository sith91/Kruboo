# services/ai-gateway/routes/monitoring_routes.py
from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime

from models.system_models import SystemMetricsRequest, SystemMetricsResponse, ProcessInfo
from core.system_monitor import SystemMonitor

router = APIRouter(tags=["monitoring"])

system_monitor = None

async def initialize():
    global system_monitor
    system_monitor = SystemMonitor()
    await system_monitor.start_monitoring()

async def cleanup():
    if system_monitor:
        await system_monitor.stop_monitoring()

@router.get("/system/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(request: SystemMetricsRequest):
    """Get comprehensive system metrics"""
    try:
        metrics_data = {}
        
        if "cpu" in request.metrics:
            metrics_data["cpu"] = await system_monitor.get_cpu_usage()
        
        if "memory" in request.metrics:
            metrics_data["memory"] = await system_monitor.get_memory_usage()
            
        if "disk" in request.metrics:
            metrics_data["disk"] = await system_monitor.get_disk_usage()
            
        if "processes" in request.metrics:
            metrics_data["processes"] = await system_monitor.get_running_processes()
        
        return SystemMetricsResponse(
            timestamp=datetime.utcnow().isoformat(),
            metrics=metrics_data
        )
        
    except Exception as e:
        logging.error(f"System metrics failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/processes")
async def get_running_processes(limit: int = 50):
    """Get running processes with resource usage"""
    try:
        processes = await system_monitor.get_running_processes(limit=limit)
        return {
            "processes": processes,
            "total": len(processes)
        }
    except Exception as e:
        logging.error(f"Process listing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/system/processes/{pid}/kill")
async def kill_process(pid: int):
    """Kill a specific process"""
    try:
        success = await system_monitor.kill_process(pid)
        return {
            "success": success,
            "pid": pid,
            "message": "Process killed successfully" if success else "Failed to kill process"
        }
    except Exception as e:
        logging.error(f"Process kill failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
