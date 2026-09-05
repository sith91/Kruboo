# AI Assistant - Desktop & Mobile

A modular AI assistant with a Python backend and dual frontends (Electron for Desktop, Flutter for Mobile).

## Project Structure
- `python_backend/`: FastAPI server handling STT, LLM reasoning, and tool execution.
- `electron_app/`: Premium glassmorphic desktop interface with Siri Orb & 3D VRM Avatar.
- `flutter_mobile/`: Cross-platform mobile interface with 3D VRM WebGL engine & Floating System Overlay.

## 📄 Project Documents
| Document | Description |
|---|---|
| [README.md](./README.md) | Setup and feature overview (this file) |
| [flutter_app_README.md](./flutter_app_README.md) | 📱 Flutter mobile app guide (3D VRM & Floating Overlay) |
| [BUILD_APK.md](./BUILD_APK.md) | 📦 Android APK build instructions (Chaquopy + foreground service) |
| [ai_assistant_plan.md](./ai_assistant_plan.md) | Full architecture and implementation plan |
| [MR_HEADSET_ROADMAP.md](./MR_HEADSET_ROADMAP.md) | 🥽 Mixed Reality headset integration roadmap |

---

## 🚀 Getting Started (Testing/Deployment)

### 1. Python Backend Setup
The backend serves as the core intelligence layer.

```bash
cd python_backend

# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Environment Variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (optional for local models)

# 4. STT Model (Vosk)
# Ensure 'vosk-model-small-en-us-0.15' folder is present in 'python_backend/'
# If not, download from https://alphacephei.com/vosk/models and extract here.

# 5. Run the server
python main.py
```
The server will run at `http://localhost:8000`.

### 2. Electron App Setup (Desktop)
The premium desktop orb and chat interface.

```bash
cd electron_app

# 1. Install Node dependencies
npm install

# 2. Start the application
npm start
```
*Note: Ensure the Python backend is running before starting the Electron app.*

### 3. Flutter App Setup (Mobile)
Cross-platform mobile application with 3D VRM rendering and floating overlay.

```bash
cd flutter_mobile

# 1. Get dependencies
flutter pub get

# 2. Run the app on Android device / emulator
flutter run
```

---

## ⚡ Real-Time Architecture & Performance
- **Full-Duplex WebSockets:** The assistant now uses a persistent bidirectional WebSocket connection for all chat and voice interactions, ensuring zero-latency communication.
- **Parallelized Web Research:** Web search results are extracted in parallel using a thread pool, reducing research lag from ~30s to <5s.
- **Async-Safe Backend:** Heavy synchronous tasks (LLM, TTS, Research) are offloaded to background threads to keep the FastAPI event loop responsive.
- **Optimized Hot-Reloading:** Configured to ignore data directories (`voices/`, `notes/`, `assets/`, `workspace/`) during development, preventing expensive AI model reloads when data is saved.

---

## 🏠 Smart Home & IoT Integration
- **Vendor Connectors:** A plug-and-play "Connector Gallery" allows non-technical users to activate smart home brands (Philips Hue, Tuya, Tasmota, WLED) without coding.
- **Automatic Discovery:** Uses mDNS/Zeroconf to automatically find and link new IoT devices on the local network.
- **Unified Control:** Control lights, switches, and sensors using natural language across different vendors.
- **Automated IoT Triggers:** Link IoT devices to system events (e.g., "Turn on the heater if the weather is cold").

---

## 🛠 Features
- **3D VRM Avatar Engine:** Hardware-accelerated WebGL Three.js + `@pixiv/three-vrm` character engine with natural breathing, touch gaze tracking, auto-blinking, facial expressions, and real-time speech lip-sync across Desktop and Mobile.
- **Floating System Overlay (`flutter_overlay_window`):** Android floating assistant head accessible over any application for quick voice queries.
- **Voice Intelligence:** Integrated Vosk (Local) and Whisper (Cloud) STT. Includes **ElevenLabs Voice Cloning** dynamically registering custom user voice recordings for premium TTS.
- **Multimodal Vision:** **Webcam/Camera Integration** capturing and analyzing visual inputs locally using **Ollama** (e.g. LLaVA or Llama 3.2 Vision) or cloud services (Gemini 1.5 Flash, OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet) with keyless Pollinations.ai free fallback.
- **Deep Research:** Autonomous web searching via Trafilatura and DuckDuckGo.
- **Multilingual:** Enhanced support for Sinhala using SinLingua.
- **Local Brain:** Support for Phi-3 Mini, Llama-3, and Mistral via GPT4All multi-model coordination with streaming support.
- **System Tools:** Control apps, take notes, and monitor system stats.
- **Automation Engine:** Rule-based background automations triggered by time, battery level, email, weather, stock prices, or calendar events.
- **Memory & Personal RAG:** SQLite-backed memory for chat history and personal facts (with automatic model-driven fact parsing via `[MEMORIZE: fact]`), utilizing `all-MiniLM-L6-v2` for semantic search.
- **Cross-Platform Sync:** Local P2P device synchronization using Zeroconf network discovery and secure QR code pairing.
- **Security:** Master passcode protection for locking sensitive system settings and personal facts.

## 📝 Commands & Usage
- "Open Firefox"
- "Search for latest AI news"
- "Take a note about my meeting tomorrow"
- "What's the weather in Colombo?"
- "Turn on the desk light" (IoT)
- "Scan for new smart devices" (IoT Discovery)
- "ඔයාට කොහොම ද?" (Sinhala support)
- "Remember that my birthday is tomorrow" (SQLite Fact Memorization)
- Snap a snapshot using the Camera button next to the input area to query with webcam vision.

---

## 🔮 Future Roadmap

### 🥽 Mixed Reality (MR) Headset Integration
Kruboo is architecturally ready for MR. The Python WebSocket backend requires no changes — any MR headset becomes just another frontend.

**Planned Platforms:** Meta Quest 3, Apple Vision Pro, Microsoft HoloLens 2, Samsung Galaxy XR

| Phase | Goal | Status |
|---|---|---|
| Phase 1 | Quick Wi-Fi connect to existing backend | 📋 Planned |
| Phase 2 | Spatial Flutter UI with hand-tracking input | 📋 Planned |
| Phase 3 | True 3D spatial assistant orb in Unity/RealityKit | 📋 Planned |
| Phase 4 | AR IoT overlays anchored to physical devices | 📋 Planned |
| Phase 5 | Contextual spatial memory & location-aware automations | 📋 Planned |

> 📖 See the full breakdown in [MR_HEADSET_ROADMAP.md](./MR_HEADSET_ROADMAP.md)

---

## 🧠 LLM Configurations & Mobile Synchronization

Kruuboo provides flexible AI routing configurations supporting both cloud providers and on-device offline models with cross-device synchronization and fallback states.

### 1. Cloud LLM Setup
Non-technical users can configure premium cloud LLMs in **under 30 seconds** by navigating to Settings and adding their API keys:
* **Gemini (Google AI Studio)**: Fast to configure, free/cheap keys.
* **OpenAI (GPT-4o)**
* **Anthropic (Claude 3.5 Sonnet)**
* **DeepSeek V3 / R1**: Natively supported via DeepSeek API (`https://api.deepseek.com` and `deepseek-chat`).

### 2. Local/Offline Models
For 100% offline, privacy-first local chat capability:
* **Ollama Mode (Recommended)**: Relays requests to a local Ollama service running on `http://localhost:11434/api/chat`. Handles local vision queries via `llava` or `llama3.2-vision`.
* **Direct GGUF Mode (CPU-only)**: Loads models like Phi-3 or Mistral directly from `~/.cache/gpt4all/` using CPU-only `llama-cpp-python` threads.

### 3. Mobile Client Synchronization & Fallbacks
Running heavy 4GB+ GGUF files directly inside a smartphone's RAM is avoided to preserve battery life and prevent memory crashes. Instead:
* **P2P Desktop Pairing**: Users link the mobile Flutter client with their desktop computer via a secure QR code scanner. When connected, the phone routes all heavy prompt and vision processing to the desktop GPU/CPU.
* **Connection Failures**: If the paired desktop is switched off, the mobile app UI catches the socket error and displays: *"Brain connection failed."*
* **Keyless Cloud Fallback**: For camera vision queries, if local models are selected but the local server is unreachable, the system automatically falls back to **Pollinations.ai** to ensure the query resolves without an API key.
