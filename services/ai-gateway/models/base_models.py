# services/ai-gateway/models/base_models.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

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
