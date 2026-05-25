# 🥽 Mixed Reality Headset Integration — Future Roadmap

> **Status:** Planned  
> **Last Updated:** 2026-05-18  
> **Author:** Kruboo AI Assistant Team

---

## Overview

The Kruboo AI Assistant is architecturally positioned for Mixed Reality (MR) integration. Because the entire intelligence layer lives in the Python backend as a pure WebSocket API, any MR headset capable of running a WebSocket client can connect to it with minimal frontend changes. This document outlines the phased roadmap to bring Kruboo into spatial computing environments.

---

## Supported Target Platforms

| Headset | OS | Best Frontend Approach | Priority |
|---|---|---|---|
| **Meta Quest 3 / 3S** | Android-based | Flutter (Android build) or Unity WebXR | 🔴 High |
| **Apple Vision Pro** | visionOS | Flutter (visionOS target) or native SwiftUI | 🔴 High |
| **Microsoft HoloLens 2** | Windows MR | Flutter Windows / Unity WebSocket plugin | 🟡 Medium |
| **Samsung Galaxy XR** | Android | Flutter Android build | 🟡 Medium |

---

## Architecture in MR Context

The headset becomes just another frontend — the backend remains unchanged.

```
[ MR Headset ]
      │
      │  WebSocket (ws://<host-ip>:8000/ws)
      ▼
[ Python FastAPI Backend ]  ← No changes required ✅
      │
      ├── LLM (Llama / OpenAI / Gemini)
      ├── Voice STT (Vosk / Whisper)
      ├── Memory & Personal RAG (SQLite)
      ├── IoT Connector Gallery
      └── Web Research Engine
```

---

## Phased Roadmap

### ✅ Phase 0 — Foundation (Current State)
The backend is already MR-ready.
- [x] FastAPI WebSocket server running on port `8000`
- [x] Voice audio processing via Vosk/Whisper
- [x] Streaming LLM responses over WebSocket
- [x] IoT control via modular connector gallery
- [x] Memory/RAG for personalized context

---

### 🚀 Phase 1 — Quick Connect (No Code Changes Required)
**Goal:** Prove connectivity from an MR headset to the existing backend.

**Steps:**
1. Run the Python backend on a Mac/PC on the local network.
2. Find the host machine's local IP:
   ```bash
   ipconfig getifaddr en0   # macOS
   ```
3. On the Quest or Vision Pro browser, navigate to:
   ```
   http://<host-ip>:8000/docs
   ```
   Verify the backend is reachable.
4. Sideload the Flutter APK on Quest (via ADB), or run via the Vision Pro simulator.
5. Update the backend WebSocket URL in Flutter from `localhost` to `<host-ip>`.

**Outcome:** A fully functional, voice-capable AI assistant running on an MR headset using the existing codebase.

---

### 🎨 Phase 2 — Spatial Flutter UI
**Goal:** Adapt the Flutter frontend for a comfortable spatial experience.

**Tasks:**
- [ ] Redesign UI as a **floating panel** (no bottom nav bars, no small touch targets)
- [ ] Use large, finger-friendly buttons optimized for hand-tracking input
- [ ] Integrate `flutter_tts` for spatial audio voice output from the headset
- [ ] Support headset microphone input for the voice pipeline (pipe mic stream to WebSocket)
- [ ] Handle gaze and pinch gestures via headset accessibility APIs
- [ ] Add a minimal HUD-style overlay mode for ambient awareness

**Target Headsets:** Meta Quest 3, Apple Vision Pro, Samsung Galaxy XR

---

### 🌐 Phase 3 — True Spatial AI (Unity / WebXR)
**Goal:** Render Kruboo as a native 3D spatial assistant inside MR environments.

**Tasks:**
- [ ] Create a Unity project using the [Meta XR SDK](https://developer.oculus.com/) or Apple RealityKit
- [ ] Implement a C# WebSocket client to connect to the FastAPI backend
- [ ] Render the **Kruboo orb as a 3D floating GameObject** anchored in world space
- [ ] Animate the orb (idle pulse, thinking, speaking states) in 3D
- [ ] Trigger commands via:
  - 🎤 **Voice** — spatial microphone always-on trigger
  - 🤚 **Hand gestures** — pinch/grab to summon or dismiss the assistant
  - 👁️ **Eye gaze** — look at an object to contextually query it
- [ ] Implement **spatial panels** for displaying search results, notes, and IoT dashboards in world space

**Target Headsets:** Meta Quest 3 (primary), HoloLens 2

---

### 🏠 Phase 4 — Spatial IoT AR Overlays
**Goal:** Overlay smart home device controls directly onto physical objects in the room.

**Tasks:**
- [ ] Integrate **room scanning / scene understanding**:
  - Meta Quest Scene API for Quest devices
  - Apple ARKit for Vision Pro
- [ ] Allow users to **anchor IoT device labels** to physical objects (e.g., a virtual "Desk Lamp" tag floating above the actual lamp)
- [ ] Enable gaze-triggered IoT commands:
  - Look at a light → say "turn it off" → IoT backend executes
- [ ] Display **live sensor data** (temperature, motion, power usage) as floating AR widgets next to devices
- [ ] Extend the Connector Gallery UI to a **3D spatial device map** of the home/office

**Backend Dependency:** Existing `iot_connector_manager.py` and `iot_control.py` require no changes.

---

### 🧠 Phase 5 — Contextual Spatial Memory
**Goal:** Make Kruboo aware of the physical space and use it to enhance memory and recommendations.

**Tasks:**
- [ ] Store **spatial anchors** in SQLite alongside personal facts (e.g., "my desk is at anchor XYZ")
- [ ] Use room context to disambiguate commands ("turn on the light" → knows which room the user is in)
- [ ] Surface relevant memories and notes as **spatial sticky notes** in world space
- [ ] Enable **location-aware automations** (e.g., enter the kitchen → assistant suggests recipes)

---

## Component Change Summary

| Component | Change Required | Phase |
|---|---|---|
| **Python Backend** | ✅ None — WebSocket API works as-is | 0 |
| **Flutter App** | Minor: spatial UI layout, larger hit targets, mic stream | 2 |
| **Voice Pipeline** | Minor: route headset mic audio to backend | 2 |
| **Orb UI** | Redesign as 3D floating world-locked object | 3 |
| **IoT Tools** | Enhancement: add AR spatial anchors for devices | 4 |
| **Memory/RAG** | Enhancement: add spatial anchor metadata to facts | 5 |

---

## Quick Start for Developers

```bash
# 1. Start the backend
cd python_backend
source venv/bin/activate
python main.py

# 2. Get your local IP
ipconfig getifaddr en0

# 3. Build Flutter APK for Quest sideloading
cd flutter_app
flutter build apk --release

# 4. Sideload to Quest via ADB
adb install build/app/outputs/flutter-apk/app-release.apk

# 5. Update WS URL in Flutter before building:
#    ws://localhost:8000/ws  →  ws://<your-ip>:8000/ws
```

---

## References

- [Meta XR SDK for Unity](https://developer.oculus.com/documentation/unity/unity-gs-overview/)
- [Flutter visionOS Support](https://docs.flutter.dev/platform-integration/visionos)
- [Apple RealityKit Docs](https://developer.apple.com/documentation/realitykit)
- [WebXR Device API](https://developer.mozilla.org/en-US/docs/Web/API/WebXR_Device_API)
- [Meta Quest Scene API](https://developer.oculus.com/documentation/unity/unity-scene-overview/)
