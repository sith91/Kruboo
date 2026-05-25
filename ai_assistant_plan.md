# AI Assistant (Flutter + Electron + Python) Implementation Plan

## Overview
This project involves building a sophisticated AI Assistant with dual frontends (Flutter and Electron) and a single Python backend. The assistant will support voice and text inputs, execute local system commands (opening apps, taking notes), perform internet searches, and interface with both cloud-based and local LLMs.

## Architecture

### 1. Frontends: Flutter & Electron
The project provides two independent user interfaces:
- **Flutter App:** Ideal for mobile deployment and cross-platform consistency. Features modern UI design and uses standard packages for voice/text input.
- **Electron App:** Ideal for a dedicated desktop experience (macOS, Windows, Linux). Features a native-feeling glassmorphic chat interface and utilizes Web APIs for voice input.
- **Communication:** Frontends connect to the Python backend via bidirectional WebSockets for real-time streaming and sync, with REST APIs used for static configurations.

### 2. Backend: Python
The Python backend will act as the brain of the assistant, handling the heavy lifting.
- **Server:** FastAPI or Flask for handling requests from the frontend applications.
- **Capabilities:**
  - **Voice Processing:** If audio is sent, use Whisper (local) or a cloud API to transcribe it to text.
  - **Intent Parsing:** Determine if the user wants to open an app, search the web, take a note, or chat with the LLM.
  - **App Interaction:** Use `subprocess` or `os` modules to open applications (macOS/Windows specific commands).
  - **Note Taking:** Create and manage markdown or text files for notes.
  - **Web Search:** Use an API like DuckDuckGo, SerpApi, or simply `googlesearch-python` to fetch results, then feed them to the LLM to summarize.
  - **IoT Control:** A modular plugin system for controlling smart home devices (Hue, Tuya, Tasmota, WLED) via a "Connector Gallery" for non-technical users.
  - **Memory Management:** SQLite-based storage for user facts (semantic search via `all-MiniLM-L6-v2`), chat history, and automation rules.
  - **Automation Engine:** Daemon thread evaluating rules (time, battery, email, weather, stock, calendar) to trigger automated actions like app control, notifications, or voice alerts.
  - **Local P2P Sync:** Cross-device pairing over the local network using Zeroconf discovery and secure base64 QR code payload exchange.
  - **Security:** SQLite-backed master passcode storage for protecting configurations.
  - **LLM Integration:**
    - **Cloud:** OpenAI API, Anthropic, or Gemini APIs.
    - **Local:** Multi-model coordination using python bindings (GPT4All) to run models like Llama-3, Phi-3, and Mistral locally for privacy and offline usage, with streaming support.

## Development Phases

### Phase 1: Setup & Basic Communication
- Create the Flutter, Electron, and Python project directories.
- Setup a basic FastAPI server in Python.
- Setup a simple chat UI in Flutter.
- Setup a premium glassmorphic chat UI in HTML/CSS/JS for Electron.
- Establish text-based communication between both frontends and the backend.

### Phase 2: Core Assistant Logic & LLM setup
- Integrate an LLM (e.g., local via Ollama or cloud via API).
- Implement dynamic routing in the backend to decide whether a query is a general text prompt or a specific command.

### Phase 3: Advanced System Interactions
- Implement the "Open App" functionality (e.g., `open -a "App Name"` on macOS).
- Implement the "Take Notes" and Personal RAG functionality (saving to local SQLite db with embeddings).
- Implement "Web Search" capability.
- Setup background Automation Engine for reactive local tasks.
- Implement Local P2P Sync for secure cross-device connectivity.

### Phase 4: Voice Integration
- Add audio recording in Flutter (using `record` or similar package).
- Add audio recording in Electron via web APIs.
- Send audio streams/files to the backend.
- Use a speech-to-text model on the backend to transcribe.

### Phase 5: Optimization & Real-Time Performance (Completed)
- **WebSocket Integration:** Moved chat and voice streaming from HTTP to bidirectional WebSockets for reduced latency.
- **Research Optimization:** Parallelized the web extraction engine to handle multiple sources concurrently.
- **Memory Optimization:** Implemented smart reloading logic to ignore data writes and keep the model persistent in memory.
- **Concurrency:** Ensured all heavy backend operations are offloaded to background threads to prevent blocking the server's main loop.
- **IoT Connectors:** Built a vendor-agnostic "Connector Gallery" architecture for non-technical smart home integration.

## Recommended Project Structure
```text
/ai_assistant/
├── README.md             # Global setup instructions
├── flutter_app/          # Mobile/Desktop UI
├── electron_app/         # Desktop UI
└── python_backend/       # Python Server
```

## Deployment & Testing Instructions

### Backend (Python)
1. **Environment:** Create a venv and install `requirements.txt`.
2. **Models:** Download the Vosk small model and place it in the `python_backend` root.
3. **Execution:** Run `python main.py` to start the FastAPI server on port 8000.

### Frontend (Electron)
1. **Dependencies:** Run `npm install` in `electron_app`.
2. **Execution:** Run `npm start`.

### Frontend (Flutter)
1. **Dependencies:** Run `flutter pub get` in `flutter_app`.
2. **Execution:** Run `flutter run`.
