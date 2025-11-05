import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from core.local_voice_engine import LocalVoiceEngine

async def test_local_engine():
    """Test the local voice engine with a simple audio file"""
    engine = LocalVoiceEngine()
    
    try:
        # Initialize
        await engine.initialize()
        print("✅ Local voice engine initialized")
        
        # Test health check
        health = await engine.health_check()
        print(f"✅ Health check: {health}")
        
        # Test with a sample audio file (you'll need to create this)
        # audio_file = "test_audio.wav"
        # if os.path.exists(audio_file):
        #     with open(audio_file, "rb") as f:
        #         audio_data = f.read()
        #     
        #     result = await engine.transcribe(audio_data)
        #     print(f"✅ Transcription test: '{result.text}'")
        
        # Test TTS
        tts_audio = await engine.synthesize("Hello, this is a test of the local voice engine.")
        print(f"✅ TTS test: Generated {len(tts_audio)} bytes of audio")
        
        print("🎉 All local engine tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_local_engine())
