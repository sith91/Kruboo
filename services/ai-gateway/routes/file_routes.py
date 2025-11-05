# services/ai-gateway/routes/file_routes.py
from fastapi import APIRouter, HTTPException
import logging

from models.system_models import FileSearchRequest
from core.file_system_controller import FileSystemController

router = APIRouter(tags=["files"])

file_system_controller = None

async def initialize():
    global file_system_controller
    file_system_controller = FileSystemController()
    await file_system_controller.initialize()

@router.post("/files/search")
async def intelligent_file_search(request: FileSearchRequest):
    """AI-enhanced file search with semantic understanding"""
    try:
        results = await file_system_controller.search_files(
            query=request.query,
            directory=request.directory,
            file_types=request.file_types,
            content_search=request.content_search,
            use_semantic=request.use_semantic
        )
        
        return {
            "query": request.query,
            "results": results,
            "total_count": len(results),
            "search_type": "semantic" if request.use_semantic else "keyword"
        }
        
    except Exception as e:
        logging.error(f"File search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/files/organize")
async def organize_files(directory: str, strategy: str = "type"):
    """Organize files using AI-powered categorization"""
    try:
        result = await file_system_controller.organize_files(
            directory=directory,
            strategy=strategy
        )
        
        return {
            "directory": directory,
            "strategy": strategy,
            "result": result,
            "organized_count": result.get('files_organized', 0)
        }
        
    except Exception as e:
        logging.error(f"File organization failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/recent")
async def get_recent_files(limit: int = 20, file_type: str = None):
    """Get recently accessed files"""
    try:
        files = await file_system_controller.get_recent_files(limit, file_type)
        return {"recent_files": files}
    except Exception as e:
        logging.error(f"Failed to get recent files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
