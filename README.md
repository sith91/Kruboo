# AI Assistant - Desktop & Mobile

A modular AI assistant with a Python backend and dual frontends (Electron for Desktop, Flutter for Mobile).

## Project Structure
- `python_backend/`: FastAPI server handling STT, LLM reasoning, and tool execution.
- `electron_app/`: Premium glassmorphic desktop interface.
- `flutter_app/`: Cross-platform mobile/desktop interface.

## 📄 Project Documents
| Document | Description |
|---|---|
| [README.md](./README.md) | Setup and feature overview (this file) |
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

### 3. Flutter App Setup (Mobile/Desktop)
Optional frontend for mobile.

```bash
cd flutter_app

# 1. Get dependencies
flutter pub get

# 2. Run the app
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
- **Voice Intelligence:** Integrated Vosk (Local) and Whisper (Cloud) STT.
- **Deep Research:** Autonomous web searching via Trafilatura and DuckDuckGo.
- **Multilingual:** Enhanced support for Sinhala using SinLingua.
- **Local Brain:** Support for Phi-3 Mini, Llama-3, and Mistral via GPT4All multi-model coordination with streaming support.
- **System Tools:** Control apps, take notes, and monitor system stats.
- **Automation Engine:** Rule-based background automations triggered by time, battery level, email, weather, stock prices, or calendar events.
- **Memory & Personal RAG:** SQLite-backed memory for chat history and personal facts, utilizing `all-MiniLM-L6-v2` for semantic search.
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
