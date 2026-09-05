# Kruuboo Mobile Assistant (Flutter)

A cross-platform Flutter application for **Kruuboo AI Assistant**, featuring an offline 3D VRM Avatar engine, a floating system overlay assistant, multimodal camera vision, Chaquopy background service, and full-duplex WebSocket LAN synchronization.

---

## 🌟 Key Features

### 1. 🎭 Real-Time 3D VRM Avatar Engine
- **Hardware-Accelerated WebGL Rendering**: Powered by Three.js and `@pixiv/three-vrm` within a transparent, low-latency WebView.
- **Natural Kinematics & Idle Breathing**: Fluid chest breathing and personality-based spine attitude (`professional`, `energetic`, `lethargic`).
- **Touch Gaze Tracking**: The 3D character's head and eyes follow your touch / drag gestures in real time.
- **Auto-Blinking & Facial Expressions**: Realistic non-periodic blinking and dynamic facial expressions (`happy`, `surprised`, `thinking`, `angry`, `neutral`).
- **TTS Speech Lip-Sync**: Bi-directional JavaScript bridge synchronizing mouth visemes (`aa`, `ih`, `ou`, `ee`, `oh`) with speech output.

### 2. 🪟 Floating System Overlay Assistant (`flutter_overlay_window`)
- **System-Wide Overlay**: Displays a draggable floating assistant bubble over other Android applications.
- **Quick Voice Interaction**: Tap the floating bubble to trigger speech recognition and get instant AI responses without switching apps.
- **Dynamic Mode Support**: Switch between the mini 3D VRM Avatar and the Siri-style glowing orb inside the floating window.

### 3. 🧠 Embedded & Remote Brain Architecture
- **Standalone Android Execution (Chaquopy)**: Can run Python backend natively inside an Android Foreground Service.
- **LAN Discovery & Sync**: Pairs with the desktop backend using mDNS Zeroconf discovery and secure QR code tokens.
- **Full-Duplex WebSockets**: Real-time token streaming and cross-device conversation sync.

### 4. 👁 Multimodal Vision & Camera Tools
- **Live Camera / Photo Analysis**: Snap photos or analyze objects locally using on-device models or cloud vision (GPT-4o / Gemini 1.5 Flash / Claude 3.5 Sonnet).

---

## 🚀 Getting Started

### Prerequisites
- Flutter SDK `>= 3.1.0`
- Android Studio / Android SDK (API 26+)
- Python 3.10+ (for backend pairing or building APK with Chaquopy)

### Installation & Run

```bash
cd flutter_mobile

# 1. Fetch dependencies
flutter pub get

# 2. Run on connected Android device / emulator
flutter run
```

---

## 📱 Permissions Configuration

Ensure the following permissions are granted for full feature functionality:
- **Display over other apps (`SYSTEM_ALERT_WINDOW`)**: Required for the Floating System Overlay Assistant.
- **Microphone (`RECORD_AUDIO`)**: Required for voice input & wake-word listening.
- **Camera (`CAMERA`)**: Required for visual inspection and QR code pairing.
- **Foreground Service (`FOREGROUND_SERVICE`)**: Keeps the background AI engine and overlay active.

---

## 📁 Project Structure

```
flutter_mobile/
├── assets/
│   ├── models/            # Default .vrm 3D character assets
│   └── vrm/               # Three.js, @pixiv/three-vrm & index.html engine
├── lib/
│   ├── main.dart          # App entrypoint & overlayMain() handler
│   ├── models/            # Persona and config models
│   ├── screens/           # Main, chat history, persona, and overlay views
│   ├── services/          # API, Overlay, Persona, and Voice trigger services
│   ├── theme/             # Glassmorphism and dark theme tokens
│   └── widgets/           # VRMAvatarWidget and OrbWidget
└── pubspec.yaml
```
