from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

# Import our modules
from core.model_selector import ModelSelector
from core.intent_analyzer import IntentAnalyzer
from core.command_processor import CommandProcessor
from providers.model_registry import ModelRegistry
from utils.config import load_config
from utils.metrics import MetricsCollector

# Configuration
config = load_config()

# Initialize FastAPI app
app = FastAPI(
    title="AI Assistant Gateway",
    description="Unified AI and voice processing service",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('cors_origins', ['*']),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
model_registry = ModelRegistry(config)
model_selector = ModelSelector(model_registry.get_providers())
intent_analyzer = IntentAnalyzer()
command_processor = CommandProcessor()
metrics = MetricsCollector()

# Pydantic models
class AIRequest(BaseModel):
    prompt: str
    context: Dict[str, Any] = {}
    model_preference: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7

class AIResponse(BaseModel):
    text: str
    model_used: str
    tokens_used: int
    confidence: float
    processing_time: float

class VoiceCommandRequest(BaseModel):
    audio_data: str  # base64 encoded
    language: str = "en-US"

class VoiceCommandResponse(BaseModel):
    transcript: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    action: str
    parameters: Dict[str, Any]

class SystemCommandRequest(BaseModel):
    command: str
    parameters: Dict[str, Any] = {}

class SystemCommandResponse(BaseModel):
    success: bool
    result: Any
    message: str

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await model_registry.initialize_providers()
    await intent_analyzer.initialize()
    logging.info("AI Gateway started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await model_registry.cleanup()

# Health endpoints
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    providers_health = {}
    for provider in model_registry.get_providers():
        providers_health[provider.config.name] = await provider.health_check()
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "ai-gateway",
        "providers": providers_health
    }

@app.get("/health/providers")
async def providers_health():
    """Detailed providers health check"""
    providers_info = []
    for provider in model_registry.get_providers():
        providers_info.append({
            "name": provider.config.name,
            "enabled": provider.config.enabled,
            "healthy": await provider.health_check(),
            "priority": provider.get_priority(),
            "models": await provider.get_available_models()
        })
    
    return {"providers": providers_info}

# Unified AI Processing
@app.post("/v1/ai/process", response_model=AIResponse)
async def process_ai_request(request: AIRequest):
    """
    Unified AI processing endpoint - handles both simple commands and complex AI requests
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        # Check if this is a simple system command
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

# Voice Command Processing
@app.post("/v1/voice/command", response_model=VoiceCommandResponse)
async def process_voice_command(request: VoiceCommandRequest):
    """
    Complete voice command processing pipeline
    """
    try:
        # 1. Speech to Text
        transcript = await _transcribe_audio(request.audio_data, request.language)
        
        # 2. Intent Analysis
        intent_result = await intent_analyzer.analyze(transcript)
        
        # 3. Return structured command
        return VoiceCommandResponse(
            transcript=transcript.text,
            intent=intent_result.intent,
            confidence=intent_result.confidence * transcript.confidence,  # Combined confidence
            entities=intent_result.entities,
            action=intent_result.action,
            parameters=intent_result.parameters
        )
        
    except Exception as e:
        logging.error(f"Voice command processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Direct Speech-to-Text
@app.post("/v1/voice/transcribe")
async def transcribe_audio(request: VoiceCommandRequest):
    """Pure speech-to-text transcription"""
    try:
        return await _transcribe_audio(request.audio_data, request.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Direct Text-to-Speech
@app.post("/v1/voice/synthesize")
async def synthesize_speech(text: str, voice: str = "default"):
    """Text-to-speech synthesis"""
    try:
        # This would integrate with your TTS engine
        audio_data = await _synthesize_speech(text, voice)
        return {
            "audio_data": audio_data,  # base64
            "format": "wav",
            "sample_rate": 24000,
            "voice": voice
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# System Commands
@app.post("/v1/system/execute", response_model=SystemCommandResponse)
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
        return SystemCommandResponse(
            success=False,
            result=None,
            message=str(e)
        )

# Model Management
@app.get("/v1/models")
async def get_available_models():
    """Get all available models across providers"""
    models = []
    for provider in model_registry.get_providers():
        if await provider.health_check():
            provider_models = await provider.get_available_models()
            models.extend([
                {
                    "name": model,
                    "provider": provider.config.name,
                    "capabilities": _get_model_capabilities(provider.config.name, model)
                }
                for model in provider_models
            ])
    
    return {"models": models}

# Helper functions
async def _is_system_command(prompt: str) -> bool:
    """Determine if prompt can be handled as a system command"""
    system_keywords = [
        'open', 'close', 'launch', 'start', 'quit', 'exit',
        'search', 'find', 'look up',
        'create', 'make', 'new',
        'delete', 'remove', 'trash',
        'move', 'copy', 'paste',
        'what time', 'what date', 'what is the weather'
    ]
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in system_keywords)

async def _process_system_command(request: AIRequest) -> AIResponse:
    """Process system commands locally"""
    result = await command_processor.execute(request.prompt, request.context)
    
    return AIResponse(
        text=result.response,
        model_used="system-command",
        tokens_used=0,
        confidence=result.confidence,
        processing_time=0.1  # Fast local processing
    )

async def _process_ai_completion(request: AIRequest) -> AIResponse:
    """Process using external AI models"""
    # Select appropriate model
    model_selection = await model_selector.select_model(
        prompt=request.prompt,
        context=request.context,
        user_preference=request.model_preference
    )
    
    # Prepare messages
    messages = [
        {"role": "system", "content": _get_system_prompt(request.context)},
        {"role": "user", "content": request.prompt}
    ]
    
    # Process with selected model
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

async def _transcribe_audio(audio_data: str, language: str) -> Any:
    """Transcribe audio to text"""
    # This would integrate with your STT engine
    # For now, return a mock response
    return {
        "text": "mock transcription",
        "confidence": 0.9,
        "language": language,
        "is_final": True
    }

async def _synthesize_speech(text: str, voice: str) -> str:
    """Synthesize speech from text"""
    # This would integrate with your TTS engine
    # Return base64 encoded audio
    return "base64_encoded_audio_data"

def _get_system_prompt(context: Dict[str, Any]) -> str:
    """Generate system prompt based on context"""
    base_prompt = """You are a helpful AI assistant with system integration capabilities.
You can help with: opening applications, searching files, managing tasks, answering questions, and more.
Be concise and helpful."""
    
    if context.get("source") == "voice":
        base_prompt += "\n\nThis is a voice command, so keep responses brief and actionable."
    
    return base_prompt

def _get_model_capabilities(provider: str, model: str) -> List[str]:
    """Get capabilities for a specific model"""
    capabilities = {
        "openai": ["general", "creative", "analysis", "coding"],
        "deepseek": ["coding", "reasoning", "analysis"],
        "anthropic": ["reasoning", "analysis", "long-form"],
        "google": ["general", "multimodal", "creative"]
    }
    return capabilities.get(provider, ["general"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.get('host', '0.0.0.0'),
        port=config.get('port', 8000),
        log_level=config.get('log_level', 'info')
    )
