# AI Assistant - Desktop & Mobile

A modular AI assistant with a Python backend and dual frontends (Electron for Desktop, Flutter for Mobile).

## Project Structure
- `python_backend/`: FastAPI server handling STT, LLM reasoning, and tool execution.
- `electron_app/`: Premium glassmorphic desktop interface.
- `flutter_app/`: Cross-platform mobile/desktop interface.

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

## 🛠 Features
- **Voice Intelligence:** Integrated Vosk (Local) and Whisper (Cloud) STT.
- **Deep Research:** Autonomous web searching via Trafilatura and DuckDuckGo.
- **Multilingual:** Enhanced support for Sinhala using SinLingua.
- **Local Brain:** Support for Phi-3 Mini and Orca-mini via GPT4All.
- **System Tools:** Control apps, take notes, and monitor system stats.

## 📝 Commands & Usage
- "Open Firefox"
- "Search for latest AI news"
- "Take a note about my meeting tomorrow"
- "What's the weather in Colombo?"
- "ඔයාට කොහොම ද?" (Sinhala support)
