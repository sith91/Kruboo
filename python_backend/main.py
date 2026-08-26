from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Request, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents.assistant import handle_user_query, stream_user_query, _gmail_plugin, _calendar_plugin, memory
from tools.object_detector import detect_objects_locally
import uvicorn
import os
import io
import json
from tools.stt import transcribe_audio_bytes
from tools.sync_manager import LocalSyncManager
from tools.automation_engine import AutomationEngine

import socket

def get_free_port(start_port: int = 8000) -> int:
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                port += 1

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI Assistant API", description="Backend for Desktop AI Assistant")

# Enable CORS for local Electron client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

requested_port = int(os.getenv("PORT", 8000))
backend_port = get_free_port(requested_port)
sync_manager = LocalSyncManager(port=backend_port)

# Initialize engine with callback to broadcast notifications via WebSocket
def broadcast_notification(data):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(data), loop)
    except: pass

auto_engine = AutomationEngine(broadcast_callback=broadcast_notification)

LOCK_PATH = "/tmp/kruboo_chat_active.lock"

def lock_training():
    try:
        with open(LOCK_PATH, "w") as f:
            f.write("active")
    except:
        pass

def unlock_training():
    try:
        if os.path.exists(LOCK_PATH):
            os.remove(LOCK_PATH)
    except:
        pass

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

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
                lock_training()
                try:
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
                        chat_id=query_data.get("chat_id", "default"),
                        image=query_data.get("image", None)
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
                finally:
                    unlock_training()
                
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
    auto_engine.start()

@app.on_event("shutdown")
async def shutdown_event():
    pass

# ── Chat History Endpoints ─────────────────────────────────────────────────

async def verify_sync_token(x_sync_token: str = Header(None), request: Request = Request):
    # Allow localhost without token for the primary app
    client_host = request.client.host
    if client_host in ("127.0.0.1", "localhost", "::1"):
        return True

    if not x_sync_token or not sync_manager.verify_token(x_sync_token):
        raise HTTPException(status_code=401, detail="Invalid Sync Token. Please link your device using the pairing code.")
    return True

@app.get("/chats", dependencies=[Depends(verify_sync_token)])
async def list_chat_sessions():
    """Return a summary of every past conversation, newest first."""
    sessions = memory.get_all_chat_sessions()
    return {"chats": sessions}

@app.get("/chats/{chat_id}/messages", dependencies=[Depends(verify_sync_token)])
async def get_chat_messages(chat_id: str):
    """Return all messages for a specific chat session."""
    messages = memory.get_history(chat_id, limit=10000)
    return {"messages": messages}

@app.delete("/chats/{chat_id}", dependencies=[Depends(verify_sync_token)])
async def delete_chat_session(chat_id: str):
    """Permanently delete all messages for a chat session."""
    memory.clear_history(chat_id)
    return {"status": "ok", "chat_id": chat_id}

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
    image: str = None

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

@app.get("/auth/calendar")
async def authenticate_calendar():
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
    lock_training()
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
                feeling=request.feeling,
                image=request.image
            )
        )
        # Broadcast to other devices
        await manager.broadcast({"type": "message", "role": "user", "content": request.query})
        await manager.broadcast({"type": "message", "role": "assistant", "content": response_text})
        
        return QueryResponse(response=response_text, action_taken=action)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        unlock_training()

class DetectObjectsRequest(BaseModel):
    image: str

@app.post("/detect_objects_local", dependencies=[Depends(verify_sync_token)])
async def detect_objects_local_endpoint(request: DetectObjectsRequest):
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result_text = await loop.run_in_executor(None, detect_objects_locally, request.image)
        # Broadcast the local action to other sync channels
        await manager.broadcast({"type": "message", "role": "assistant", "content": result_text})
        return {"response": result_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stream_query", dependencies=[Depends(verify_sync_token)])
async def process_query_stream(request: QueryRequest):
    print(f"DEBUG: Processing stream query: {request.query} (Provider: {request.llm_provider})")
    # Broadcast user message first
    await manager.broadcast({"type": "message", "role": "user", "content": request.query})
    
    async def broadcast_wrapper():
        lock_training()
        try:
            full_response = ""
            async for chunk in stream_user_query(
                query=request.query,
                language=request.language,
                assistant_name=request.assistant_name,
                provider=request.llm_provider,
                model=request.llm_model,
                api_key=request.api_key,
                allow_web_search=request.allow_web_search,
                feeling=request.feeling,
                image=request.image
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
        finally:
            unlock_training()

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

# Alias endpoints for /memories (expected by mobile and native clients)
@app.get("/memories", dependencies=[Depends(verify_sync_token)])
async def get_memories_alias(category: str = None):
    try:
        facts = memory.get_all_facts(category)
        return {"memories": facts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memories", dependencies=[Depends(verify_sync_token)])
async def add_memory_alias(request: dict):
    try:
        fact = request.get("fact")
        category = request.get("category", "general")
        if not fact:
            raise HTTPException(status_code=400, detail="Fact is required")
        memory.save_fact(fact, category)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memories/{fact_id}", dependencies=[Depends(verify_sync_token)])
async def delete_memory_alias(fact_id: int):
    try:
        memory.delete_fact(fact_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/automations", dependencies=[Depends(verify_sync_token)])
async def get_all_automations(device: str = None):
    automations = memory.get_automations()
    if device:
        automations = [a for a in automations if a.get('device') == device]
    return {"automations": automations}

@app.post("/automations", dependencies=[Depends(verify_sync_token)])
async def create_automation(request: dict):
    try:
        memory.add_automation(
            request['name'],
            request['trigger_type'],
            request['trigger_config'],
            request['action_type'],
            request['action_config'],
            request.get('device', 'both')
        )
        return {"success": True}

        # --- Plugin Management Endpoints ---
        @app.get("/plugins", dependencies=[Depends(verify_sync_token)])
        async def list_plugins():
            try:
                plugins = memory.list_plugins()
                return {"plugins": plugins}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/plugins/activate", dependencies=[Depends(verify_sync_token)])
        async def activate_plugin_endpoint(request: dict):
            try:
                name = request.get("name")
                if not name:
                    raise HTTPException(status_code=400, detail="Plugin name required")
                memory.activate_plugin(name)
                return {"success": True}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.post("/plugins/deactivate", dependencies=[Depends(verify_sync_token)])
        async def deactivate_plugin_endpoint(request: dict):
            try:
                name = request.get("name")
                if not name:
                    raise HTTPException(status_code=400, detail="Plugin name required")
                memory.deactivate_plugin(name)
                return {"success": True}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
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

# --- General Settings Endpoints ---
@app.get("/settings/workspace", dependencies=[Depends(verify_sync_token)])
async def get_workspace_setting():
    path = memory.get_setting("allowed_workspace_dir")
    return {"allowed_workspace_dir": path or ""}

@app.post("/settings/workspace", dependencies=[Depends(verify_sync_token)])
async def update_workspace_setting(data: dict):
    path = data.get("allowed_workspace_dir", "").strip()
    if path:
        abs_path = os.path.abspath(path)
        memory.set_setting("allowed_workspace_dir", abs_path)
        return {"status": "success", "allowed_workspace_dir": abs_path}
    else:
        memory.set_setting("allowed_workspace_dir", "")
        return {"status": "success", "allowed_workspace_dir": ""}

@app.post("/run_command", dependencies=[Depends(verify_sync_token)])
async def run_command_endpoint(data: dict):
    import re
    import subprocess
    cmd = data.get("command", "")
    lower = cmd.lower().strip()
    dangerous_patterns = [
        r"\brm\b",
        r"\bsudo\b",
        r"\bcurl\b",
        r"\bwget\b",
        r"\bchmod\b",
        r"\bchown\b",
        r"[>|]"
    ]
    is_dangerous = any(re.search(pat, lower) for pat in dangerous_patterns)
    if is_dangerous:
        return {
            "success": False,
            "error": "Security Exception: This command contains restricted patterns (rm, sudo, curl, wget, chmod, redirection, or piping) and has been blocked for safety.",
            "stdout": "",
            "stderr": ""
        }
    
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "error": "" if res.returncode == 0 else f"Exit code {res.returncode}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": ""
        }

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
        # Clear cached voice ID to force re-cloning on next TTS request
        memory.set_setting("elevenlabs_voice_id", "")
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

@app.get("/avatar")
async def get_avatar():
    try:
        file_path = os.path.join("assets", "assistant_avatar.png")
        if os.path.exists(file_path):
            from fastapi.responses import FileResponse
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="Avatar not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_pet")
async def upload_pet(file: UploadFile = File(...), state: str = Form(...)):
    try:
        if state not in ["idle", "listening", "thinking", "speaking"]:
            raise HTTPException(status_code=400, detail="Invalid state")
        
        os.makedirs(os.path.join("assets", "pet"), exist_ok=True)
        
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".gif", ".png", ".jpg", ".jpeg", ".apng"]:
            raise HTTPException(status_code=400, detail="Unsupported image format")
        
        for old_ext in [".gif", ".png", ".jpg", ".jpeg", ".apng"]:
            old_file = os.path.join("assets", "pet", f"pet_{state}{old_ext}")
            if os.path.exists(old_file):
                os.remove(old_file)
                
        file_path = os.path.join("assets", "pet", f"pet_{state}{ext}")
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
            
        return {"success": True, "path": f"/pet/{state}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pet/{state}")
async def get_pet(state: str):
    try:
        pet_dir = os.path.join("assets", "pet")
        for ext in [".gif", ".png", ".jpg", ".jpeg", ".apng"]:
            file_path = os.path.join(pet_dir, f"pet_{state}{ext}")
            if os.path.exists(file_path):
                from fastapi.responses import FileResponse
                return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="Pet avatar not found")
    except HTTPException:
        raise
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
                
                # Dynamic Voice Registration Check
                voice_id = memory.get_setting("elevenlabs_voice_id")
                if not voice_id:
                    print("Registering voice sample to ElevenLabs...")
                    import requests
                    url = "https://api.elevenlabs.io/v1/voices/add"
                    headers = {"xi-api-key": elevenlabs_key}
                    files = {
                        "files": ("user_voice.wav", open(voice_path, "rb"), "audio/wav")
                    }
                    data = {
                        "name": "Kruuboo Voice Clone",
                        "description": "User voice clone created via Kruuboo AI Assistant Desktop"
                    }
                    r = requests.post(url, headers=headers, files=files, data=data)
                    if r.status_code == 200:
                        voice_id = r.json().get("voice_id")
                        if voice_id:
                            print(f"Voice cloned successfully. ID: {voice_id}")
                            memory.set_setting("elevenlabs_voice_id", voice_id)
                        else:
                            raise Exception("Could not find voice_id in ElevenLabs response.")
                    else:
                        raise Exception(f"ElevenLabs API error: {r.status_code} - {r.text}")
                
                from elevenlabs import generate, set_api_key
                set_api_key(elevenlabs_key)
                
                audio = generate(
                    text=text,
                    voice=voice_id,
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
            try:
                with open(tmp_path, mode="rb") as file_like:
                    yield from file_like
            finally:
                # Clean up after streaming or on client disconnect/cancellation
                import os
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

        return StreamingResponse(iterfile(), media_type="audio/mpeg")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    should_reload = os.getenv("DEV_MODE", "false").lower() == "true"
    backend_port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=backend_port, 
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
