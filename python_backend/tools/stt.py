import vosk
import json
import wave
import io
import os

# Initialize Vosk Model once on startup
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "vosk-model-small-en-us-0.15")

print(f"Loading Vosk STT Model from {MODEL_DIR}...")
if not os.path.exists(MODEL_DIR):
    # Fallback to local search if relative path fails in certain environments
    MODEL_DIR = "vosk-model-small-en-us-0.15"

try:
    model = vosk.Model(MODEL_DIR)
except Exception as e:
    print(f"Vosk Init Error: {e}. STT will be unavailable.")
    model = None

def transcribe_audio_bytes(audio_bytes: bytes, language: str = "en-US", api_key: str = None) -> str:
    """
    Multilingual STT routing.
    1. If API Key is provided, use OpenAI Whisper (Supports Translation).
    2. If language is Sinhala, try SinLingua.
    3. Fallback to Vosk (English).
    """
    
    # 1. Premium Fallback: OpenAI Whisper (High Quality & Multilingual)
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                if "si" in language.lower():
                    # Transcribe natively in Sinhala — preserve original text for SinLingua processing
                    print("Using Whisper TRANSCRIBE (native Sinhala)...")
                    with open(tmp_path, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="si"   # ISO 639-1 code for Sinhala
                        )
                        text = transcription.text
                else:
                    print(f"Using Whisper TRANSCRIBE for {language}...")
                    with open(tmp_path, "rb") as audio_file:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file
                        )
                        text = transcription.text
                
                print(f"Whisper Result: [{text}]")
                return text
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            print(f"Whisper STT failed, falling back: {e}")

    # 2. Native Sinhala Fallback (SinLingua)
    if "si" in language.lower():
        try:
            from sinlingua.sinhala_audio import audio_to_text as sinhala_stt
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                print("Using SinLingua for Sinhala STT...")
                text = sinhala_stt.conversion(tmp_path)
                print(f"SinLingua Result: [{text}]")
                if text:
                    return text
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as e:
            print(f"SinLingua STT failed: {e}")

    # 3. Default: Vosk (English Only)
    if not model:
        return "STT Engine Offline: Model not found"

    try:
        audio_file = io.BytesIO(audio_bytes)
        with wave.open(audio_file, "rb") as wf:
            # Vosk expects 16-bit PCM mono
            rec = vosk.KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(False)
            
            # Read and process frames
            frames = wf.readframes(wf.getnframes())
            # For Vosk, we can just process the whole block
            rec.AcceptWaveform(frames)
            
            result = json.loads(rec.FinalResult())
            text = result.get("text", "")
            print(f"Vosk Transcription Result: [{text}]")
            return text
            
    except Exception as e:
        import traceback
        print(f"Vosk STT Pipeline Error: {e}")
        traceback.print_exc()
        return f"STT Pipeline Error: {str(e)}"
