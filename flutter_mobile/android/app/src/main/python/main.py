from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents.assistant import handle_user_query, stream_user_query, _gmail_plugin, _calendar_plugin, memory
import uvicorn
import os
import io
import json
from tools.stt import transcribe_audio_bytes
from tools.sync_manager import LocalSyncManager
from tools.automation_engine import AutomationEngine

app = FastAPI(title="AI Assistant API", description="Backend for Desktop AI Assistant")
sync_manager = LocalSyncManager(port=8000)

# Initialize engine with callback to broadcast notifications via WebSocket
def broadcast_notification(data):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)
    except: pass

auto_engine = AutomationEngine(broadcast_callback=broadcast_notification)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # Verify token
    if not sync_manager.verify_token(token) and token != "localhost":
        await websocket.close(code=1008)
        return
    
    await manager.connect(websocket)
    try:
        while True:
            # Handle incoming messages (bidirectional interaction)
            data = await websocket.receive_json()
            
            # 1. Handle Chat Queries
            if data.get("type") == "chat_query":
                query_data = data.get("payload", {})
                query = query_data.get("query")
                if not query: continue
                
                print(f"WS: Received query: {query}")
                
                # Broadcast user message first to all devices
                await manager.broadcast({"type": "message", "role": "user", "content": query})
                
                full_response = ""
                # Stream the assistant response directly over the WebSocket
                async for chunk in stream_user_query(
                    query=query,
                    language=query_data.get("language", "en-US"),
                    assistant_name=query_data.get("assistant_name", "Assistant"),
                    provider=query_data.get("llm_provider", "local"),
                    model=query_data.get("llm_model", "llama-3"),
                    api_key=query_data.get("api_key", ""),
                    allow_web_search=query_data.get("allow_web_search", True),
                    feeling=query_data.get("feeling", "professional"),
                    chat_id=query_data.get("chat_id", "default")
                ):
                    try:
                        # Extract token for broadcasting later
                        chunk_str = chunk.decode() if isinstance(chunk, bytes) else chunk
                        chunk_data = json.loads(chunk_str.strip())
                        if 'token' in chunk_data:
                            full_response += chunk_data['token']
                        
                        # Send token to the specific requester
                        await websocket.send_json({"type": "chat_token", "payload": chunk_data})
                    except:
                        pass
                
                # After stream ends, broadcast full assistant message to sync other devices
                await manager.broadcast({"type": "message", "role": "assistant", "content": full_response})
                await websocket.send_json({"type": "chat_done"})

            # 2. Handle Keep-Alive or other message types
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    # sync_manager.start_discovery()
    auto_engine.start()
    pass
@app.on_event("shutdown")
async def shutdown_event():
    # sync_manager.stop_discovery()
    pass

async def verify_sync_token(x_sync_token: str = Header(None), request: Request = Request):
    # Allow localhost without token for the primary app
    client_host = request.client.host
    if client_host in ("127.0.0.1", "localhost", "::1"):
        return True
    
    if not x_sync_token or not sync_manager.verify_token(x_sync_token):
        raise HTTPException(status_code=401, detail="Invalid Sync Token. Please link your device using the pairing code.")
    return True

@app.get("/sync/status")
async def get_sync_status(request: Request):
    client_host = request.client.host
    is_local = client_host in ("127.0.0.1", "localhost", "::1")
    return {
        "status": "online",
        "local_ip": sync_manager.get_local_ip(),
        "pairing_token": sync_manager.sync_token if is_local else "****",
        "pairing_qr": sync_manager.get_pairing_qr_base64() if is_local else None
    }

class QueryRequest(BaseModel):
    query: str
    is_voice: bool = False
    language: str = "English"
    assistant_name: str = "Assistant"
    llm_provider: str = "local"
    llm_model: str = "llama-3"
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
    if not _gmail_plugin:
        return {"status": "error", "message": "Gmail integration is not available on mobile."}
    success, message = _gmail_plugin.authenticate()
    if success:
        return {"status": "success", "message": message}
    else:
        return {"status": "error", "message": message}

@app.get("/auth/calendar")
async def authenticate_calendar():
    if not _calendar_plugin:
        return {"status": "error", "message": "Calendar integration is not available on mobile."}
    success, message = _calendar_plugin.authenticate()
    if success:
        return {"status": "success", "message": message}
    else:
        return {"status": "error", "message": message}

@app.post("/transcribe", dependencies=[Depends(verify_sync_token)])
async def process_audio(file: UploadFile = File(...), language: str = Form("en-US"), api_key: str = Form(None)):
    try:
        audio_bytes = await file.read()
        transcription = transcribe_audio_bytes(audio_bytes, language, api_key)
        return {"text": transcription}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse, dependencies=[Depends(verify_sync_token)])
async def process_query(request: QueryRequest):
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response_text, action = await loop.run_in_executor(
            None,
            lambda: handle_user_query(
                query=request.query,
                language=request.language,
                assistant_name=request.assistant_name,
                provider=request.llm_provider,
                model=request.llm_model,
                api_key=request.api_key,
                allow_web_search=request.allow_web_search,
                feeling=request.feeling
            )
        )
        # Broadcast to other devices
        await manager.broadcast({"type": "message", "role": "user", "content": request.query})
        await manager.broadcast({"type": "message", "role": "assistant", "content": response_text})
        
        return QueryResponse(response=response_text, action_taken=action)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream_query", dependencies=[Depends(verify_sync_token)])
async def process_query_stream(request: QueryRequest):
    print(f"DEBUG: Processing stream query: {request.query} (Provider: {request.llm_provider})")
    # Broadcast user message first
    await manager.broadcast({"type": "message", "role": "user", "content": request.query})
    
    async def broadcast_wrapper():
        full_response = ""
        async for chunk in stream_user_query(
            query=request.query,
            language=request.language,
            assistant_name=request.assistant_name,
            provider=request.llm_provider,
            model=request.llm_model,
            api_key=request.api_key,
            allow_web_search=request.allow_web_search,
            feeling=request.feeling
        ):
            # Try to extract content from chunk if it's JSON
            try:
                # Handle both bytes and strings
                chunk_str = chunk.decode() if isinstance(chunk, bytes) else chunk
                data = json.loads(chunk_str.replace('data: ', '').strip())
                if 'token' in data:
                    full_response += data['token']
            except:
                pass
            yield chunk
        
        # After stream ends, broadcast full assistant message
        await manager.broadcast({"type": "message", "role": "assistant", "content": full_response})

    return StreamingResponse(broadcast_wrapper(), media_type="application/x-ndjson")
    
@app.get("/memory/facts", dependencies=[Depends(verify_sync_token)])
async def get_memories(category: str = None):
    try:
        facts = memory.get_all_facts(category)
        return {"facts": facts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/facts", dependencies=[Depends(verify_sync_token)])
async def add_memory(request: dict):
    try:
        fact = request.get("fact")
        category = request.get("category", "general")
        if not fact:
            raise HTTPException(status_code=400, detail="Fact is required")
        memory.save_fact(fact, category)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memory/facts/{fact_id}", dependencies=[Depends(verify_sync_token)])
async def delete_memory(fact_id: int):
    try:
        memory.delete_fact(fact_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/automations", dependencies=[Depends(verify_sync_token)])
async def get_all_automations():
    return {"automations": memory.get_automations()}

@app.post("/automations", dependencies=[Depends(verify_sync_token)])
async def create_automation(request: dict):
    try:
        memory.add_automation(
            request['name'], 
            request['trigger_type'], 
            request['trigger_config'], 
            request['action_type'], 
            request['action_config']
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- IoT Connector Endpoints ---
from tools.iot_connector_manager import IoTConnectorManager
iot_manager = IoTConnectorManager()

@app.get("/iot/connectors", dependencies=[Depends(verify_sync_token)])
async def get_iot_connectors():
    return {"connectors": iot_manager.get_available_connectors()}

@app.get("/iot/active", dependencies=[Depends(verify_sync_token)])
async def get_active_iot_connectors():
    return {"active": iot_manager.get_active_connectors()}

@app.post("/iot/activate", dependencies=[Depends(verify_sync_token)])
async def activate_iot_connector(request: dict):
    vendor_id = request.get("vendor_id")
    config_data = request.get("config", {})
    return iot_manager.activate_connector(vendor_id, config_data)

@app.post("/iot/dispatch", dependencies=[Depends(verify_sync_token)])
async def dispatch_iot_command(request: dict):
    device_name = request.get("device_name", "")
    action = request.get("action", "")
    value = request.get("value")
    result = iot_manager.dispatch_command(device_name, action, value)
    return {"status": "success", "result": result}

# --- Security Endpoints ---
@app.post("/security/set_passcode")
async def set_passcode(data: dict):
    passcode = data.get("passcode")
    if not passcode: return {"status": "error", "message": "Passcode required"}
    import hashlib
    hashed = hashlib.sha256(passcode.encode()).hexdigest()
    memory.set_passcode(hashed)
    return {"status": "success"}

@app.post("/security/verify_passcode")
async def verify_passcode(data: dict):
    passcode = data.get("passcode")
    stored_hash = memory.get_passcode()
    if not stored_hash: return {"status": "success", "message": "No passcode set"}
    import hashlib
    current_hash = hashlib.sha256(passcode.encode()).hexdigest()
    if current_hash == stored_hash:
        return {"status": "success"}
    return {"status": "error", "message": "Invalid passcode"}

@app.get("/security/status")
async def security_status():
    stored_hash = memory.get_passcode()
    return {"is_locked": stored_hash is not None}

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

@app.post("/tts", dependencies=[Depends(verify_sync_token)])
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
                
                import asyncio
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: app.tts_model.tts_to_file(
                        text=text,
                        speaker_wav=voice_path,
                        language=xtts_lang,
                        file_path=output_path
                    )
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
    should_reload = os.getenv("DEV_MODE", "false").lower() == "true"
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=should_reload, 
        reload_dirs=["."], 
        reload_excludes=[
            "voices/*", 
            "assets/*", 
            "notes/*", 
            "workspace/*", 
            "*.db", 
            "memory.db*", 
            "venv/*", 
            "__pycache__/*", 
            "*.log",
            ".sync_config.json"
        ]
    )
