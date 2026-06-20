# Android APK Build Instructions

This document outlines the steps and configuration required to successfully build the Android APK for this project, particularly dealing with **Chaquopy** (for embedding the Python backend) and specific Flutter plugin dependencies.

## 1. Building the APK

To build the APK, simply navigate to the `flutter_app` directory and run:

```bash
# For a debug build
flutter build apk --debug

# For a release build (requires signing setup)
flutter build apk --release
```

The compiled APK will be located at:
`build/app/outputs/flutter-apk/app-debug.apk`

---

## 2. Key Build Configurations & Fixes Applied

Building this project required several specific configurations to resolve compatibility issues between the host OS, Chaquopy, and Flutter plugins. If you encounter issues on a fresh machine, refer to these fixes.

### A. Chaquopy and Python Version Constraints
We are using **Chaquopy 17.0.0** to embed the Python backend. Chaquopy 17.0 has a strict requirement: **The local Python compiler (`buildPython`) used during the Gradle build must match the exact major/minor version of the Python embedded in the app.**

- **Embedded Python:** `3.10`
- **Fix:** Because macOS often defaults to Python 3.9, we downloaded a standalone Python 3.10 binary from [Astral's python-build-standalone](https://github.com/astral-sh/python-build-standalone) into `flutter_app/standalone_python/`.
- `build.gradle.kts` is configured to look for this standalone Python first:
  ```kotlin
  for (candidate in listOf(
      rootProject.file("../standalone_python/python/bin/python3").absolutePath,
      "python3.10", ...
  )) 
  ```
  *(If you install Python 3.10 system-wide, the build will automatically pick that up instead).*

### B. Pydantic & Rust Compilation 
- **Issue:** FastAPI relies on `pydantic`. Pydantic `v2.x` relies on `pydantic-core`, which is written in Rust. Chaquopy does not currently provide pre-compiled Android ARM wheels for `pydantic-core`, causing pip installations to fail.
- **Fix:** We pinned `pydantic==1.10.13` in `android/app/build.gradle.kts`. Pydantic v1 is pure Python and fully supported by Chaquopy, and works perfectly with `fastapi==0.104.1`.

### C. DJL Tokenizer Dependency
- **Issue:** The `build.gradle.kts` originally referenced a non-existent package `ai.djl.android:tokenizers`.
- **Fix:** Changed the implementation to the correct Hugging Face package: `implementation("ai.djl.huggingface:tokenizers:0.27.0")`.

### D. Flutter Plugin Upgrades (SDK Compatibility)
Newer Flutter SDK versions removed the deprecated V1 Android Plugin APIs (`PluginRegistry.Registrar`), which caused older plugins to fail compilation.
- **`speech_to_text`:** Upgraded to `^7.4.0` to remove legacy V1 references.
- **`record`:** Upgraded to `^6.2.1` to satisfy strict interface constraints with `record_platform_interface` related to the `startStream` method. 

## 3. Clean Rebuilds

If you run into weird caching issues (especially with Chaquopy pip packages), clear the build environments:

```bash
flutter clean
flutter pub get
flutter build apk --debug
```
