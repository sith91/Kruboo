import asyncio
import logging
from typing import Optional, Dict, Any
from .whisper_engine import WhisperLocalEngine, TranscriptionResult
from .tts_engine import PiperTTSEngine
from .audio_pipeline import AudioProcessor

class LocalVoiceEngine:
    def __init__(self):
        self.stt_engine = WhisperLocalEngine()
        self.tts_engine = PiperTTSEngine()
        self.audio_processor = AudioProcessor()
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize all local voice components"""
        try:
            logging.info("Initializing local voice engine...")
            
            # Initialize STT engine
            await self.stt_engine.initialize()
            
            # Initialize TTS engine  
            await self.tts_engine.initialize()
            
            self.is_initialized = True
            logging.info("Local voice engine initialized successfully")
            
        except Exception as e:
            logging.error(f"Local voice engine initialization failed: {e}")
            raise
    
    async def transcribe(self, audio_data: bytes, language: Optional[str] = "en") -> TranscriptionResult:
        """Complete transcription pipeline"""
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # Preprocess audio
            processed_audio = await self.audio_processor.preprocess_audio(audio_data)
            
            # Check for voice activity
            has_voice = await self.audio_processor.detect_voice_activity(processed_audio)
            if not has_voice:
                return TranscriptionResult(
                    text="",
                    confidence=0.0,
                    language=language,
                    is_final=True
                )
            
            # Transcribe
            return await self.stt_engine.transcribe(processed_audio, language)
            
        except Exception as e:
            logging.error(f"Transcription pipeline failed: {e}")
            raise
    
    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Complete synthesis pipeline"""
        if not self.is_initialized:
            await self.initialize()
        
        return await self.tts_engine.synthesize(text, voice)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of local voice engine"""
        return {
            "stt_available": self.stt_engine.model_loaded,
            "tts_available": self.tts_engine.model_loaded,
            "initialized": self.is_initialized,
            "models_loaded": True  # Simplified for now
        }
