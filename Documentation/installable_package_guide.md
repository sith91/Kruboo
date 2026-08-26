# Installable Package Guide for Electron + Python Backend

## Overview
- **Frontend**: Electron (HTML/CSS/JS) located in `electron_app/`.
- **Backend**: Python FastAPI (`python_backend/app.py`).
- Goal: Produce a **single installer** per platform that contains both UI and backend, requiring no extra setup from the end‑user.

## Prerequisites

| Tool | Minimum Version |
|------|-----------------|
| Node.js | 20.x |
| npm / yarn | latest |
| Python | 3.9‑3.12 |
| PyInstaller | 6.5+ |
| Electron‑builder | 24+ |
| Docker (optional) | for cross‑compiling ARM |

## 1. Build the Python Backend
```bash
# From project root
pip install -r python_backend/requirements.txt pyinstaller

# macOS (run on target mac)
pyinstaller --onefile --name backend python_backend/app.py

# Windows (run on Windows or via wine)
pyinstaller --onefile --name backend.exe python_backend/app.py

# Linux x86_64
pyinstaller --onefile --name backend python_backend/app.py

# Linux ARM64 (e.g., Raspberry Pi)
# run on the device or use a cross‑compile Docker image
pyinstaller --onefile --name backend python_backend/app.py
```
The binaries appear in `python_backend/dist/`.  

**Copy the binary into the Electron resources folder**
```bash
mkdir -p electron_app/resources/python
cp python_backend/dist/backend* electron_app/resources/python/
```

## 2. Embed the Backend in Electron
```javascript
// main.js excerpt
const path = require('path');
const { spawn } = require('child_process');

const backendPath = path.join(__dirname, 'resources', 'python',
  process.platform === 'win32' ? 'backend.exe' : 'backend');

const backend = spawn(backendPath, [], { stdio: 'inherit' });
backend.on('error', (e) => {
  console.error('Failed to start backend:', e);
});
```
Add fallback UI handling if the binary is missing.

## 3. Electron‑Builder Configuration (`package.json`)
```json
{
  "name": "kruboo-ai-assistant",
  "version": "1.0.0",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "dist": "electron-builder",
    "build-backend": "bash scripts/build_backend.sh",
    "package": "bash scripts/package_electron.sh"
  },
  "devDependencies": {
    "electron": "^29.1.0",
    "electron-builder": "^26.8.1"
  },
  "dependencies": {
    "electron-updater": "^6.2.0"
    // other deps …
  },
  "build": {
    "appId": "com.kruboo.ai.assistant",
    "productName": "Kruboo",
    "files": ["**/*"],
    "extraResources": [
      { "from": "electron_app/resources/python", "to": "resources/python" }
    ],
    "mac": { "target": "dmg" },
    "win": { "target": "nsis" },
    "linux": { "target": ["AppImage","deb","rpm"] }
  }
}
```
`extraResources` ensures the backend binary is packaged.

## 4. Platform‑Specific Packaging
| Platform | Command | Result |
|----------|---------|--------|
| macOS (`.dmg`) | `npm run package` (on macOS) | `dist/Kruboo-<ver>.dmg` |
| Windows (`.exe`) | `npm run package` (on Windows) | `dist/Kruboo Setup <ver>.exe` |
| Linux (`AppImage`, `deb`, `rpm`) | `npm run package` (on Linux) | files under `dist/` |
| ARM (Raspberry Pi) | Build backend on device, then `npm run package --linux --arm64` | `dist/Kruboo-<ver>.AppImage` or tarball |

## 5. Automatic Updates (optional)
Add `electron-updater` and configure a GitHub release publish target:
```json
"publish": [{
  "provider": "github",
  "owner": "your-github",
  "repo": "your-repo"
}]
```
In `main.js`:
```javascript
const { autoUpdater } = require('electron-updater');
autoUpdater.checkForUpdatesAndNotify();
```

## 6. CI/CD Pipeline (GitHub Actions)
```yaml
name: Build & Release
on:
  push:
    tags:
      - 'v*'   # e.g., v1.0.0

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest, windows-latest, ubuntu-latest]
    steps:
      - uses: actions/checkout@v3

      - name: Set up Node
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install npm deps
        run: npm ci

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Build Python backend
        run: |
          pip install -r python_backend/requirements.txt pyinstaller
          pyinstaller --onefile python_backend/app.py -n backend
          mkdir -p electron_app/resources/python
          cp dist/backend* electron_app/resources/python/

      - name: Package Electron app
        run: npm run package

      - name: Upload release assets
        uses: softprops/action-gh-release@v2
        with:
          files: dist/*
```

## 7. Verification Checklist
| Test | Command |
|------|---------|
| Build macOS dmg | `npm run package` (on macOS) |
| Build Windows exe | `npm run package` (on Windows) |
| Build Linux AppImage | `npm run package` (on Linux) |
| Verify backend starts | Launch the packaged app, check console for “Uvicorn running on …” |
| CI sanity | Push a tag `v0.1.0`, ensure GitHub Actions creates assets for each OS. |

## 8. Distribution Checklist
- [ ] Python binaries built for each target arch.
- [ ] `electron_app/resources/python/` contains correct executable.
- [ ] `package.json` `extraResources` correctly points to that folder.
- [ ] CI workflow produces signed artifacts (signing optional).
- [ ] Update URL in `electron-updater` config.
- [ ] Provide SHA‑256 checksums for each installer.

---
*You can now keep this document as the definitive reference while you set up the build pipeline.*
