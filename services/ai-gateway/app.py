# services/ai-gateway/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from utils.config import load_config

# Import route modules
from routes import ai_routes, voice_routes, system_routes, workflow_routes, file_routes, monitoring_routes

# Configuration
config = load_config()

# Initialize FastAPI app
app = FastAPI(
    title="AI Assistant Gateway",
    description="Unified AI and voice processing service with Workflow Automation",
    version="2.5.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('cors_origins', ['*']),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(ai_routes.router, prefix="/v1")
app.include_router(voice_routes.router, prefix="/v1")
app.include_router(system_routes.router, prefix="/v1")
app.include_router(workflow_routes.router, prefix="/v1")
app.include_router(file_routes.router, prefix="/v1")
app.include_router(monitoring_routes.router, prefix="/v1")

@app.on_event("startup")
async def startup_event():
    """Initialize all services on startup"""
    # Each route module handles its own initialization
    await ai_routes.initialize()
    await workflow_routes.initialize()
    await monitoring_routes.initialize()
    logging.info("AI Gateway with Workflow Automation started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup all services on shutdown"""
    await ai_routes.cleanup()
    await workflow_routes.cleanup()
    await monitoring_routes.cleanup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.get('host', '0.0.0.0'),
        port=config.get('port', 8000),
        log_level=config.get('log_level', 'info')
    )
