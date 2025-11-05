from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import base64
import logging
import asyncio
from datetime import datetime
import aiohttp
import json

# Import our new local engine
from core.local_voice_engine import LocalVoiceEngine, TranscriptionResult
from core.audio_pipeline import AudioProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-service")

app = FastAPI(
    title="Voice Service", 
    version="2.0.0", 
    description="Local-first voice processing integrated with AI Gateway"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class AudioInput(BaseModel):
    audio_data: str  # base64 encoded
    format: str = "wav"
    sample_rate: int = 16000
    language: str = "en"
    provider: str = "local"

class SynthesisRequest(BaseModel):
    text: str
    voice: str = "default"
    rate: int = 200
    volume: float = 1.0
    provider: str = "local"

class SynthesisResult(BaseModel):
    audio_data: str  # base64 encoded
    format: str = "wav"
    sample_rate: int = 24000
    provider_used: str

class VoiceCommandRequest(BaseModel):
    audio_data: str  # base64 encoded
    language: str = "en"
    provider: str = "local"
    context: Dict[str, Any] = {}

class VoiceCommandResponse(BaseModel):
    transcript: str
    intent: str
    response: str
    audio_response: Optional[str]  # base64 encoded
    confidence: float
    provider_used: str

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    local_engine: Dict[str, Any]
    ai_gateway: Dict[str, Any]
    active_providers: Dict[str, str]

# Initialize engines
local_engine = LocalVoiceEngine()
audio_processor = AudioProcessor()

# AI Gateway Client
class AIGatewayClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_connected = False
    
    async def ensure_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if AI Gateway is available"""
        try:
            await self.ensure_session()
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.is_connected = True
                    return {
                        "status": "connected",
                        "service_status": data.get("status", "unknown"),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    self.is_connected = False
                    return {
                        "status": "error", 
                        "error": f"HTTP {response.status}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
        except Exception as e:
            self.is_connected = False
            return {
                "status": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def process_command(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send text to AI Gateway for intent processing and workflow execution"""
        await self.ensure_session()
        
        payload = {
            "prompt": text,
            "context": context or {},
            "model_preference": "fast",  # Prefer faster models for voice
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/ai/process", 
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "text": result.get("text", ""),
                        "intent": self._extract_intent(result),
                        "confidence": result.get("confidence", 0.8),
                        "raw_response": result
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"AI Gateway error {response.status}: {error_text}")
                    return {
                        "success": False,
                        "error": f"AI Gateway returned {response.status}",
                        "text": "I'm having trouble processing that right now.",
                        "intent": "error",
                        "confidence": 0.0
                    }
                    
        except Exception as e:
            logger.error(f"AI Gateway communication failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "I can't reach the AI service at the moment.",
                "intent": "error", 
                "confidence": 0.0
            }
    
    def _extract_intent(self, ai_response: Dict[str, Any]) -> str:
        """Extract intent from AI response"""
        # You can enhance this based on your AI Gateway's response structure
        text = ai_response.get("text", "").lower()
        
        # Simple intent detection from response text
        if any(word in text for word in ["open", "launch", "start"]):
            return "open_application"
        elif any(word in text for word in ["close", "quit", "exit"]):
            return "close_application" 
        elif any(word in text for word in ["search", "find", "look for"]):
            return "search"
        elif any(word in text for word in ["workflow", "automate", "schedule"]):
            return "workflow"
        else:
            return "general_query"

# Plugin system placeholder
class PluginManager:
    def __init__(self):
        self.stt_plugins = {}
        self.tts_plugins = {}
        self.active_stt = "local"
        self.active_tts = "local"
    
    async def get_stt_provider(self, provider_name: str):
        if provider_name == "local":
            return local_engine
        return self.stt_plugins.get(provider_name)
    
    async def get_tts_provider(self, provider_name: str):
        if provider_name == "local":
            return local_engine
        return self.tts_plugins.get(provider_name)
    
    async def get_available_providers(self):
        return {
            "stt": ["local"] + list(self.stt_plugins.keys()),
            "tts": ["local"] + list(self.tts_plugins.keys())
        }

# Initialize clients and managers
ai_client = AIGatewayClient()
plugin_manager = PluginManager()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Initialize local voice engine
        await local_engine.initialize()
        logger.info("Local voice engine initialized successfully")
        
        # Test AI Gateway connection
        ai_health = await ai_client.health_check()
        if ai_health["status"] == "connected":
            logger.info("AI Gateway connection established")
        else:
            logger.warning(f"AI Gateway not available: {ai_health.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        # Service can still start, but some features may be limited

@app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup resources"""
    if ai_client.session:
        await ai_client.session.close()
    logger.info("Voice Service shut down successfully")

# Health and info endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Comprehensive health check"""
    local_health = await local_engine.health_check()
    ai_health = await ai_client.health_check()
    available_providers = await plugin_manager.get_available_providers()
    
    overall_status = "healthy" if (
        local_health.get("initialized", False) and 
        ai_health.get("status") == "connected"
    ) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        service="voice-service",
        timestamp=datetime.utcnow().isoformat(),
        local_engine=local_health,
        ai_gateway=ai_health,
        active_providers={
            "stt": plugin_manager.active_stt,
            "tts": plugin_manager.active_tts
        }
    )

@app.get("/providers")
async def get_available_providers():
    """Get available STT/TTS providers"""
    providers = await plugin_manager.get_available_providers()
    return {
        "providers": providers,
        "defaults": {
            "stt": "local",
            "tts": "local"
        }
    }

# Core voice endpoints
@app.post("/v1/transcribe")
async def transcribe_audio(audio_input: AudioInput):
    """Transcribe audio to text using specified provider"""
    try:
        audio_bytes = base64.b64decode(audio_input.audio_data)
        provider = await plugin_manager.get_stt_provider(audio_input.provider)
        
        if not provider:
            provider = local_engine
            used_provider = "local"
        else:
            used_provider = audio_input.provider
        
        result = await provider.transcribe(audio_bytes, audio_input.language)
        
        return {
            "text": result.text,
            "confidence": result.confidence,
            "language": result.language,
            "is_final": result.is_final,
            "provider_used": used_provider
        }
        
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/v1/synthesize", response_model=SynthesisResult)
async def synthesize_speech(request: SynthesisRequest):
    """Convert text to speech using specified provider"""
    try:
        provider = await plugin_manager.get_tts_provider(request.provider)
        if not provider:
            provider = local_engine
            used_provider = "local"
        else:
            used_provider = request.provider
        
        audio_data = await provider.synthesize(request.text, request.voice)
        
        return SynthesisResult(
            audio_data=base64.b64encode(audio_data).decode('utf-8'),
            format="wav",
            sample_rate=24000,
            provider_used=used_provider
        )
        
    except Exception as e:
        logger.error(f"Speech synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")

# Integrated voice command endpoint
@app.post("/v1/command", response_model=VoiceCommandResponse)
async def process_voice_command(request: VoiceCommandRequest):
    """
    Complete voice command pipeline:
    Voice → STT → AI Gateway (intent) → Response → TTS → Audio
    """
    try:
        # 1. STT: Convert audio to text
        audio_bytes = base64.b64decode(request.audio_data)
        stt_provider = await plugin_manager.get_stt_provider(request.provider)
        
        if not stt_provider:
            stt_provider = local_engine
        
        transcription = await stt_provider.transcribe(audio_bytes, request.language)
        
        if not transcription.text.strip():
            return VoiceCommandResponse(
                transcript="",
                intent="no_speech",
                response="I didn't hear anything. Please try again.",
                audio_response=None,
                confidence=0.0,
                provider_used=request.provider
            )
        
        logger.info(f"Transcribed: '{transcription.text}'")
        
        # 2. Send to AI Gateway for intent processing
        context = {
            "source": "voice",
            "language": request.language,
            "confidence": transcription.confidence,
            **request.context
        }
        
        ai_result = await ai_client.process_command(transcription.text, context)
        
        if not ai_result["success"]:
            # Use fallback response if AI Gateway fails
            response_text = ai_result["text"]
            intent = "error"
            confidence = 0.3
        else:
            response_text = ai_result["text"]
            intent = ai_result["intent"]
            confidence = ai_result["confidence"] * transcription.confidence
        
        # 3. TTS: Convert AI response to speech (if we have a meaningful response)
        audio_response = None
        if response_text and response_text != "I didn't hear anything. Please try again.":
            tts_provider = await plugin_manager.get_tts_provider(request.provider)
            if not tts_provider:
                tts_provider = local_engine
            
            audio_response_data = await tts_provider.synthesize(response_text)
            audio_response = base64.b64encode(audio_response_data).decode('utf-8')
        
        return VoiceCommandResponse(
            transcript=transcription.text,
            intent=intent,
            response=response_text,
            audio_response=audio_response,
            confidence=confidence,
            provider_used=request.provider
        )
        
    except Exception as e:
        logger.error(f"Voice command processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice command processing failed: {str(e)}")

# Real-time WebSocket endpoints
@app.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    """WebSocket for real-time voice transcription only"""
    await websocket.accept()
    
    try:
        if not local_engine.is_initialized:
            await local_engine.initialize()
        
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio_chunk":
                audio_bytes = base64.b64decode(data["audio_data"])
                
                try:
                    result = await local_engine.transcribe(audio_bytes, data.get("language", "en"))
                    
                    await websocket.send_json({
                        "type": "transcription",
                        "text": result.text,
                        "confidence": result.confidence,
                        "is_final": result.is_final,
                        "provider": "local"
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                        "provider": "local"
                    })
                    
    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")

@app.websocket("/ws/command")
async def websocket_command(websocket: WebSocket):
    """Real-time voice command pipeline"""
    await websocket.accept()
    
    try:
        if not local_engine.is_initialized:
            await local_engine.initialize()
        
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio_chunk":
                audio_bytes = base64.b64decode(data["audio_data"])
                
                try:
                    # STT
                    transcription = await local_engine.transcribe(audio_bytes, data.get("language", "en"))
                    
                    if transcription.text.strip():
                        logger.info(f"Real-time transcription: '{transcription.text}'")
                        
                        # Send interim transcription
                        await websocket.send_json({
                            "type": "interim_transcription",
                            "text": transcription.text,
                            "confidence": transcription.confidence
                        })
                        
                        # Send to AI Gateway
                        ai_result = await ai_client.process_command(
                            transcription.text,
                            {"source": "voice_realtime", "language": data.get("language", "en")}
                        )
                        
                        # TTS response
                        audio_response = None
                        if ai_result["success"] and ai_result["text"]:
                            audio_response_data = await local_engine.synthesize(ai_result["text"])
                            audio_response = base64.b64encode(audio_response_data).decode('utf-8')
                        
                        await websocket.send_json({
                            "type": "command_response",
                            "transcript": transcription.text,
                            "response": ai_result["text"],
                            "audio_response": audio_response,
                            "intent": ai_result.get("intent", "unknown"),
                            "confidence": ai_result.get("confidence", 0.5),
                            "success": ai_result["success"]
                        })
                    
                except Exception as e:
                    logger.error(f"Real-time command error: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
    except WebSocketDisconnect:
        logger.info("Command WebSocket disconnected")

# Plugin management endpoints (for Phase 2)
@app.post("/plugins/register")
async def register_plugin(plugin_type: str, plugin_name: str, plugin_config: Dict[str, Any]):
    """Register a new voice plugin"""
    return {
        "status": "registered", 
        "plugin_type": plugin_type,
        "plugin_name": plugin_name,
        "message": "Plugin registration will be implemented in Phase 2"
    }

@app.post("/providers/set-default")
async def set_default_provider(provider_type: str, provider_name: str):
    """Set default provider for STT or TTS"""
    if provider_type == "stt":
        plugin_manager.active_stt = provider_name
    elif provider_type == "tts":
        plugin_manager.active_tts = provider_name
    
    return {
        "status": "updated",
        "provider_type": provider_type,
        "default_provider": provider_name
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
