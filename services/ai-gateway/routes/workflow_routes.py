# services/ai-gateway/routes/workflow_routes.py
from fastapi import APIRouter, HTTPException
import logging
from datetime import datetime

from models.workflow_models import WorkflowRequest, WorkflowResponse, WorkflowExecutionRequest
from core.workflow_engine import WorkflowEngine
from core.model_selector import ModelSelector
from providers.model_registry import ModelRegistry
from utils.config import load_config

router = APIRouter(tags=["workflows"])

# Global instances
workflow_engine = None
model_selector = None

async def initialize():
    global workflow_engine, model_selector
    config = load_config()
    
    # Initialize model registry for AI-powered workflow analysis
    model_registry = ModelRegistry(config)
    await model_registry.initialize_providers()
    model_selector = ModelSelector(model_registry.get_providers())
    
    # Initialize workflow engine
    workflow_engine = WorkflowEngine(model_selector)
    await workflow_engine.initialize()

async def cleanup():
    if workflow_engine:
        await workflow_engine.cleanup()

@router.post("/workflows/analyze", response_model=WorkflowResponse)
async def analyze_workflow(request: WorkflowRequest):
    """AI-powered workflow analysis and optimization"""
    try:
        analysis_result = await workflow_engine.analyze_workflow(
            request.steps,
            request.context
        )
        
        return WorkflowResponse(
            workflow_id=analysis_result['workflow_id'],
            optimized_steps=analysis_result['optimized_steps'],
            estimated_duration=analysis_result['estimated_duration'],
            complexity_score=analysis_result['complexity_score'],
            suggestions=analysis_result['suggestions']
        )
        
    except Exception as e:
        logging.error(f"Workflow analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflows/execute")
async def execute_workflow(request: WorkflowExecutionRequest):
    """Execute a workflow with parameters"""
    try:
        result = await workflow_engine.execute_workflow(
            request.workflow_id,
            request.parameters
        )
        
        return {
            "workflow_id": request.workflow_id,
            "status": "completed",
            "result": result,
            "execution_time": result.get('execution_time', 0)
        }
        
    except Exception as e:
        logging.error(f"Workflow execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/workflows/create")
async def create_workflow(request: WorkflowRequest):
    """Create and save a new workflow"""
    try:
        workflow_id = await workflow_engine.create_workflow(
            request.name,
            request.steps,
            request.trigger_type,
            request.description
        )
        
        return {
            "workflow_id": workflow_id,
            "name": request.name,
            "status": "created"
        }
        
    except Exception as e:
        logging.error(f"Workflow creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/workflows")
async def list_workflows():
    """Get all available workflows"""
    try:
        workflows = await workflow_engine.get_workflows()
        return {"workflows": workflows}
    except Exception as e:
        logging.error(f"Failed to list workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
