from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents.assistant import handle_user_query, stream_user_query, _gmail_plugin
import uvicorn
import os
import io
from tools.stt import transcribe_audio_bytes

app = FastAPI(title="AI Assistant API", description="Backend for Desktop AI Assistant")

class QueryRequest(BaseModel):
    query: str
    is_voice: bool = False
    language: str = "English"
    assistant_name: str = "Assistant"
    llm_provider: str = "openai"
    llm_model: str = "gpt-3.5-turbo"
    api_key: str = ""
    allow_web_search: bool = True
    feeling: str = "professional"

class QueryResponse(BaseModel):
    response: str
    action_taken: str = None

@app.get("/")
def read_root():
    return {"status": "AI Assistant Backend is Running"}

@app.get("/auth/gmail")
async def authenticate_gmail():
    success, message = _gmail_plugin.authenticate()
    if success:
        return {"status": "success", "message": message}
    else:
        return {"status": "error", "message": message}

@app.post("/transcribe")
async def process_audio(file: UploadFile = File(...), language: str = Form("en-US"), api_key: str = Form(None)):
    try:
        audio_bytes = await file.read()
        transcription = transcribe_audio_bytes(audio_bytes, language, api_key)
        return {"text": transcription}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        response_text, action = handle_user_query(
            query=request.query,
            language=request.language,
            assistant_name=request.assistant_name,
            provider=request.llm_provider,
            model=request.llm_model,
            api_key=request.api_key,
            allow_web_search=request.allow_web_search,
            feeling=request.feeling
        )
        return QueryResponse(response=response_text, action_taken=action)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream_query")
async def process_query_stream(request: QueryRequest):
    return StreamingResponse(
        stream_user_query(
            query=request.query,
            language=request.language,
            assistant_name=request.assistant_name,
            provider=request.llm_provider,
            model=request.llm_model,
            api_key=request.api_key,
            allow_web_search=request.allow_web_search,
            feeling=request.feeling
        ),
        media_type="application/x-ndjson"
    )

@app.post("/upload_voice")
async def upload_voice(file: UploadFile = File(...)):
    try:
        os.makedirs("voices", exist_ok=True)
        file_path = os.path.join("voices", "user_voice.wav")
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_avatar")
async def upload_avatar(file: UploadFile = File(...)):
    try:
        os.makedirs("assets", exist_ok=True)
        file_path = os.path.join("assets", "assistant_avatar.png")
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
        return {"success": True, "path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts")
async def process_tts(request: dict):
    try:
        text = request.get("text", "")
        language = request.get("language", "en")
        
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")

        # Tiered TTS Strategy: Cloud Cloning (ElevenLabs) > Local Cloning (XTTS) > Standard TTS (gTTS)
        voice_path = os.path.join("voices", "user_voice.wav")
        elevenlabs_key = request.get("elevenKey") or os.getenv("ELEVEN_API_KEY")

        # 1. Cloud Cloning (Highest Quality, requires key)
        if os.path.exists(voice_path) and elevenlabs_key:
            try:
                print(f"Using ElevenLabs Voice Cloning for: {language}")
                from elevenlabs import Voice, VoiceSettings, generate, set_api_key
                set_api_key(elevenlabs_key)
                
                audio = generate(
                    text=text,
                    voice=Voice(
                        voice_id='clone_detected', 
                        settings=VoiceSettings(stability=0.71, similarity_boost=0.5, style=0.0, use_speaker_boost=True)
                    ),
                    model="eleven_multilingual_v2"
                )
                return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg")
            except Exception as e:
                print(f"ElevenLabs failed: {e}. Falling back...")

        # 2. Local Voice Cloning (Private, Offline, requires voice sample)
        if os.path.exists(voice_path):
            try:
                if not hasattr(app, "tts_model"):
                    print("Loading Local Voice Cloning Model (Coqui XTTS v2)...")
                    from TTS.api import TTS
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    if torch.backends.mps.is_available(): device = "mps"
                    app.tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                
                print(f"Using Local Clone for: {language}")
                output_path = os.path.join("voices", "output.wav")
                xtts_lang = "en"
                if "si" in language.lower(): xtts_lang = "en" 
                
                app.tts_model.tts_to_file(
                    text=text,
                    speaker_wav=voice_path,
                    language=xtts_lang,
                    file_path=output_path
                )
                return StreamingResponse(open(output_path, "rb"), media_type="audio/wav")
            except Exception as e:
                print(f"Local XTTS failed: {e}. Falling back...")

        # 3. Standard Multilingual TTS (Free, Reliable)
        tts_lang = "si" if "si" in language.lower() else "en"
        
        from gtts import gTTS
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tts = gTTS(text=text, lang=tts_lang)
            tts.save(tmp.name)
            tmp_path = tmp.name
        
        def iterfile():
            with open(tmp_path, mode="rb") as file_like:
                yield from file_like
            # Clean up after streaming
            import os
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        return StreamingResponse(iterfile(), media_type="audio/mpeg")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
