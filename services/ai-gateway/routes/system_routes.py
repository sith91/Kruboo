# services/ai-gateway/routes/system_routes.py
from fastapi import APIRouter, HTTPException
import logging

from models.base_models import SystemCommandRequest, SystemCommandResponse
from core.command_processor import CommandProcessor
from core.application_manager import ApplicationManager
from core.file_system_controller import FileSystemController

router = APIRouter(tags=["system"])

# Global instances
command_processor = None
application_manager = None
file_system_controller = None

async def initialize():
    global command_processor, application_manager, file_system_controller
    command_processor = CommandProcessor()
    application_manager = ApplicationManager()
    file_system_controller = FileSystemController()
    
    await command_processor.initialize()
    await application_manager.initialize()
    await file_system_controller.initialize()

async def cleanup():
    if command_processor:
        await command_processor.cleanup()
    if application_manager:
        await application_manager.cleanup()

@router.post("/system/execute", response_model=SystemCommandResponse)
async def execute_system_command(request: SystemCommandRequest):
    """Execute system commands"""
    try:
        result = await command_processor.execute(
            request.command,
            request.parameters
        )
        return SystemCommandResponse(
            success=True,
            result=result,
            message="Command executed successfully"
        )
    except Exception as e:
        logging.error(f"System command execution failed: {str(e)}")
        return SystemCommandResponse(
            success=False,
            result=None,
            message=str(e)
        )

@router.post("/system/applications/{app_name}/launch")
async def launch_application(app_name: str):
    """Launch a specific application"""
    try:
        success = await application_manager.launch_application(app_name)
        return {
            "success": success,
            "application": app_name,
            "message": f"Application {app_name} launched successfully" if success else f"Failed to launch {app_name}"
        }
    except Exception as e:
        logging.error(f"Application launch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/system/applications/{app_name}/close")
async def close_application(app_name: str):
    """Close a specific application"""
    try:
        success = await application_manager.close_application(app_name)
        return {
            "success": success,
            "application": app_name,
            "message": f"Application {app_name} closed successfully" if success else f"Failed to close {app_name}"
        }
    except Exception as e:
        logging.error(f"Application close failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/applications")
async def get_running_applications():
    """Get list of running applications"""
    try:
        applications = await application_manager.get_running_applications()
        return {
            "running_applications": applications,
            "total": len(applications)
        }
    except Exception as e:
        logging.error(f"Failed to get running applications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/info")
async def get_system_info():
    """Get basic system information"""
    try:
        info = await command_processor.get_system_info()
        return {
            "system_info": info,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
    except Exception as e:
        logging.error(f"Failed to get system info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check for system services
@router.get("/system/health")
async def system_health_check():
    """Health check for system services"""
    services_status = {
        "command_processor": command_processor is not None,
        "application_manager": application_manager is not None,
        "file_system_controller": file_system_controller is not None
    }
    
    all_healthy = all(services_status.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services_status
    }
