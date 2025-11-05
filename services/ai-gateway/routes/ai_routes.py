# services/ai-gateway/routes/ai_routes.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import asyncio
import logging

from models.base_models import AIRequest, AIResponse
from core.model_selector import ModelSelector
from providers.model_registry import ModelRegistry
from utils.config import load_config
from utils.metrics import MetricsCollector

router = APIRouter(tags=["ai"])

# Global instances
model_registry = None
model_selector = None
metrics = None

async def initialize():
    global model_registry, model_selector, metrics
    config = load_config()
    model_registry = ModelRegistry(config)
    model_selector = ModelSelector(model_registry.get_providers())
    metrics = MetricsCollector()
    await model_registry.initialize_providers()

async def cleanup():
    if model_registry:
        await model_registry.cleanup()

@router.post("/ai/process", response_model=AIResponse)
async def process_ai_request(request: AIRequest):
    """Unified AI processing endpoint"""
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Check if this is a system command
        if await _is_system_command(request.prompt):
            response = await _process_system_command(request)
        else:
            # Use AI model for complex requests
            response = await _process_ai_completion(request)

        processing_time = asyncio.get_event_loop().time() - start_time

        # Update metrics
        await metrics.record_request(
            provider=response.model_used,
            processing_time=processing_time,
            tokens_used=response.tokens_used
        )

        return response

    except Exception as e:
        logging.error(f"AI processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
async def _is_system_command(prompt: str) -> bool:
    system_keywords = ['open', 'close', 'launch', 'start', 'quit', 'exit', 'search', 'find']
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in system_keywords)

async def _process_system_command(request: AIRequest) -> AIResponse:
    # This would integrate with command processor
    return AIResponse(
        text="System command processed",
        model_used="system-command",
        tokens_used=0,
        confidence=0.9,
        processing_time=0.1
    )

async def _process_ai_completion(request: AIRequest) -> AIResponse:
    model_selection = await model_selector.select_model(
        prompt=request.prompt,
        context=request.context,
        user_preference=request.model_preference
    )

    messages = [
        {"role": "system", "content": _get_system_prompt(request.context)},
        {"role": "user", "content": request.prompt}
    ]

    response = await model_selection.provider.chat_completion(
        messages=messages,
        model=model_selection.model,
        max_tokens=request.max_tokens,
        temperature=request.temperature
    )

    return AIResponse(
        text=response.text,
        model_used=response.model,
        tokens_used=response.tokens_used,
        confidence=response.confidence,
        processing_time=response.processing_time
    )

def _get_system_prompt(context: Dict[str, Any]) -> str:
    base_prompt = "You are a helpful AI assistant with system integration capabilities."
    if context.get("source") == "voice":
        base_prompt += " This is a voice command, so keep responses brief and actionable."
    return base_prompt
