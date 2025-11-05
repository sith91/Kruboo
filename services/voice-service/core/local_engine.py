import asyncio
import logging
import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
import whisper
import torch

@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    language: str
    is_final: bool = True

class WhisperLocalEngine:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.supported_languages = ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko"]
    
    async def initialize(self):
        """Load Whisper model asynchronously"""
        try:
            logging.info("Loading Whisper model...")
            # Use smaller model for faster loading - can upgrade to larger models later
            self.model = whisper.load_model("base")
            self.model_loaded = True
            logging.info("Whisper model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            raise
    
    async def transcribe(self, audio_data: bytes, language: Optional[str] = "en") -> TranscriptionResult:
        """Transcribe audio using local Whisper model"""
        if not self.model_loaded:
            await self.initialize()
        
        try:
            # Convert bytes to numpy array for Whisper
            import io
            import soundfile as sf
            
            # Load audio from bytes
            audio_io = io.BytesIO(audio_data)
            audio_array, sample_rate = sf.read(audio_io)
            
            # Ensure mono audio
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            # Resample to 16kHz if needed (Whisper expects 16kHz)
            if sample_rate != 16000:
                from librosa import resample
                audio_array = resample(audio_array, orig_sr=sample_rate, target_sr=16000)
            
            # Convert to float32
            audio_array = audio_array.astype(np.float32)
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_array,
                language=language if language in self.supported_languages else None,
                fp16=torch.cuda.is_available()  # Use GPU if available
            )
            
            return TranscriptionResult(
                text=result["text"].strip(),
                confidence=0.9,  # Whisper doesn't provide confidence scores
                language=result.get("language", "en"),
                is_final=True
            )
            
        except Exception as e:
            logging.error(f"Transcription failed: {e}")
            raise
