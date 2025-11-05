from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import base64
import io
import wave
import logging
import asyncio
from datetime import datetime

# Voice processing imports
import speech_recognition as sr
import pyttsx3
import numpy as np
from pydub import AudioSegment
import librosa

app = FastAPI(title="Voice Service", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoiceConfig(BaseModel):
    language: str = "en-US"
    sample_rate: int = 16000
    channels: int = 1

class AudioInput(BaseModel):
    audio_data: str  # base64 encoded
    format: str = "webm"
    sample_rate: int = 16000
    language: str = "en-US"

class TranscriptionResult(BaseModel):
    text: str
    confidence: float
    language: str
    is_final: bool

class SynthesisRequest(BaseModel):
    text: str
    voice: str = "default"
    rate: int = 200
    volume: float = 1.0

class SynthesisResult(BaseModel):
    audio_data: str  # base64 encoded
    format: str = "wav"
    sample_rate: int = 24000

class VoiceCommandResult(BaseModel):
    transcript: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    action: str
    parameters: Dict[str, Any]

# Voice processing engines
class SpeechToTextEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        self.supported_languages = {
            "en-US": "english",
            "es-ES": "spanish", 
            "fr-FR": "french",
            "de-DE": "german",
            "it-IT": "italian"
        }

    async def transcribe(self, audio_data: bytes, language: str = "en-US") -> TranscriptionResult:
        try:
            # Convert audio data to AudioData for speech_recognition
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Convert to WAV format
            wav_io = io.BytesIO()
            audio_segment.export(wav_io, format="wav")
            wav_io.seek(0)
            
            with sr.AudioFile(wav_io) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.record(source)

            # Try multiple recognition services
            text = await self._recognize_with_fallback(audio, language)
            
            return TranscriptionResult(
                text=text,
                confidence=0.9,  # Google doesn't provide confidence
                language=language,
                is_final=True
            )
            
        except Exception as e:
            logging.error(f"Transcription failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    async def _recognize_with_fallback(self, audio, language: str) -> str:
        """Try multiple speech recognition services"""
        try:
            # Try Google Speech Recognition first
            return self.recognizer.recognize_google(audio, language=language)
        except sr.UnknownValueError:
            raise HTTPException(status_code=400, detail="Speech not understood")
        except sr.RequestError as e:
            logging.warning(f"Google Speech Recognition failed: {e}")
            
            # Fallback to Sphinx (offline)
            try:
                return self.recognizer.recognize_sphinx(audio)
            except:
                raise HTTPException(status_code=500, detail="All speech recognition services failed")

class TextToSpeechEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        
        # Configure TTS engine
        self.engine.setProperty('rate', 200)
        self.engine.setProperty('volume', 1.0)
        
        # Get available voices
        self.voices = self.engine.getProperty('voices')
        self.voice_map = {
            'default': self.voices[0].id,
            'male': self.voices[0].id if len(self.voices) > 0 else None,
            'female': self.voices[1].id if len(self.voices) > 1 else self.voices[0].id
        }

    async def synthesize(self, text: str, voice: str = "default", rate: int = 200, volume: float = 1.0) -> bytes:
        try:
            # Set properties
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            voice_id = self.voice_map.get(voice, self.voice_map['default'])
            if voice_id:
                self.engine.setProperty('voice', voice_id)

            # Synthesize to in-memory file
            output = io.BytesIO()
            self.engine.save_to_file(text, 'temp.wav')
            self.engine.runAndWait()
            
            # Read the generated file
            with open('temp.wav', 'rb') as f:
                audio_data = f.read()
                
            return audio_data
            
        except Exception as e:
            logging.error(f"Speech synthesis failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")

class VoiceCommandProcessor:
    def __init__(self):
        self.stt_engine = SpeechToTextEngine()
        self.intent_patterns = self._load_intent_patterns()

    async def process_voice_command(self, audio_data: bytes, language: str = "en-US") -> VoiceCommandResult:
        # 1. Speech to Text
        transcription = await self.stt_engine.transcribe(audio_data, language)
        
        # 2. Intent Analysis
        intent_result = await self.analyze_intent(transcription.text)
        
        return VoiceCommandResult(
            transcript=transcription.text,
            intent=intent_result["intent"],
            confidence=intent_result["confidence"] * transcription.confidence,
            entities=intent_result["entities"],
            action=intent_result["action"],
            parameters=intent_result["parameters"]
        )

    async def analyze_intent(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        
        # Simple intent matching (can be enhanced with ML)
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns["patterns"]:
                if pattern in text_lower:
                    return {
                        "intent": intent,
                        "confidence": 0.9,
                        "entities": self._extract_entities(text, intent),
                        "action": patterns["action"],
                        "parameters": self._extract_parameters(text, intent)
                    }
        
        # Default to general query
        return {
            "intent": "general_query",
            "confidence": 0.3,
            "entities": {"text": text},
            "action": "ai_process",
            "parameters": {"prompt": text}
        }

    def _load_intent_patterns(self) -> Dict:
        return {
            "open_application": {
                "patterns": ["open", "launch", "start"],
                "action": "open_app"
            },
            "close_application": {
                "patterns": ["close", "quit", "exit"],
                "action": "close_app"
            },
            "search_web": {
                "patterns": ["search for", "find", "look up"],
                "action": "web_search"
            },
            "system_info": {
                "patterns": ["system info", "what's running"],
                "action": "system_info"
            }
        }

    def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        # Simple entity extraction
        if intent == "open_application":
            words = text.lower().split()
            stop_words = ["open", "launch", "start"]
            app_words = [word for word in words if word not in stop_words]
            return {"app_name": " ".join(app_words).title()}
        
        elif intent == "search_web":
            words = text.lower().split()
            stop_words = ["search", "for", "find", "look", "up"]
            query_words = [word for word in words if word not in stop_words]
            return {"query": " ".join(query_words)}
            
        return {}

    def _extract_parameters(self, text: str, intent: str) -> Dict[str, Any]:
        return self._extract_entities(text, intent)

# Initialize engines
stt_engine = SpeechToTextEngine()
tts_engine = TextToSpeechEngine()
command_processor = VoiceCommandProcessor()

@app.on_event("startup")
async def startup_event():
    logging.info("Voice Service started")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "voice-service",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/v1/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(audio_input: AudioInput):
    """Transcribe audio to text"""
    try:
        audio_bytes = base64.b64decode(audio_input.audio_data)
        return await stt_engine.transcribe(audio_bytes, audio_input.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/synthesize", response_model=SynthesisResult)
async def synthesize_speech(request: SynthesisRequest):
    """Convert text to speech"""
    try:
        audio_data = await tts_engine.synthesize(
            request.text, 
            request.voice, 
            request.rate, 
            request.volume
        )
        
        return SynthesisResult(
            audio_data=base64.b64encode(audio_data).decode('utf-8'),
            format="wav",
            sample_rate=24000
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/command", response_model=VoiceCommandResult)
async def process_voice_command(audio_input: AudioInput):
    """Complete voice command processing pipeline"""
    try:
        audio_bytes = base64.b64decode(audio_input.audio_data)
        return await command_processor.process_voice_command(audio_bytes, audio_input.language)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    """WebSocket for real-time voice processing"""
    await websocket.accept()
    
    try:
        while True:
            # Receive audio data from client
            data = await websocket.receive_json()
            
            if data["type"] == "audio_chunk":
                # Process audio chunk in real-time
                audio_bytes = base64.b64decode(data["audio_data"])
                
                try:
                    transcription = await stt_engine.transcribe(audio_bytes, data.get("language", "en-US"))
                    
                    await websocket.send_json({
                        "type": "transcription",
                        "text": transcription.text,
                        "confidence": transcription.confidence,
                        "is_final": transcription.is_final
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
    except WebSocketDisconnect:
        logging.info("Voice WebSocket disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
