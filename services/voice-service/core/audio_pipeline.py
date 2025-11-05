import asyncio
import logging
import numpy as np
from typing import Optional
import webrtcvad
import librosa
from pydub import AudioSegment
import io

class AudioProcessor:
    def __init__(self):
        self.vad = webrtcvad.Vad(2)  # Aggressiveness mode 2 (medium)
    
    async def preprocess_audio(self, audio_data: bytes, sample_rate: int = 16000) -> bytes:
        """Preprocess audio for better STT performance"""
        try:
            # Convert to AudioSegment
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Ensure mono
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Resample to target rate
            if audio.frame_rate != sample_rate:
                audio = audio.set_frame_rate(sample_rate)
            
            # Normalize volume
            audio = audio.normalize()
            
            # Remove silence (optional - can improve accuracy)
            # audio = self._remove_silence(audio)
            
            # Export back to bytes
            output = io.BytesIO()
            audio.export(output, format="wav")
            
            return output.getvalue()
            
        except Exception as e:
            logging.error(f"Audio preprocessing failed: {e}")
            return audio_data  # Return original if processing fails
    
    def _remove_silence(self, audio_segment: AudioSegment) -> AudioSegment:
        """Remove silence from audio using simple threshold"""
        # Convert to numpy array
        samples = np.array(audio_segment.get_array_of_samples())
        
        # Calculate RMS energy
        frame_length = 1024
        hop_length = 256
        rms_energy = librosa.feature.rms(
            y=samples.astype(np.float32),
            frame_length=frame_length,
            hop_length=hop_length
        )[0]
        
        # Find non-silent frames
        threshold = np.mean(rms_energy) * 0.5  # Adjustable threshold
        non_silent_frames = rms_energy > threshold
        
        if not np.any(non_silent_frames):
            return audio_segment  # Return original if all silent
        
        # Reconstruct audio without silence
        # This is a simplified implementation
        return audio_segment
    
    async def detect_voice_activity(self, audio_data: bytes, sample_rate: int = 16000) -> bool:
        """Detect if audio contains voice activity"""
        try:
            # WebRTC VAD expects 16kHz, 16-bit mono PCM
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Convert to required format
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # Get raw data
            raw_data = audio.raw_data
            
            # Check voice activity in 30ms frames
            frame_duration = 30  # ms
            frame_size = int(16000 * frame_duration / 1000) * 2  # 16-bit = 2 bytes
            
            for i in range(0, len(raw_data) - frame_size, frame_size):
                frame = raw_data[i:i + frame_size]
                if self.vad.is_speech(frame, 16000):
                    return True
            
            return False
            
        except Exception as e:
            logging.warning(f"Voice activity detection failed: {e}")
            return True  # Assume voice activity if detection fails
