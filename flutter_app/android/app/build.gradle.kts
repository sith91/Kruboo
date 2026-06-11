plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    // Chaquopy: embeds CPython 3.8 into the APK so Python backend runs on-device
    id("com.chaquo.python")
}

android {
    namespace = "com.example.ai_assistant_app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = "com.example.ai_assistant_app"
        minSdk = 26  // Chaquopy requires minSdk >= 24; 26 for onnxruntime-android
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // ── Chaquopy configuration ───────────────────────────────────────────
        ndk {
            // Target the two main Android ARM architectures
            abiFilters += listOf("arm64-v8a", "armeabi-v7a")
        }

        python {
            // CPython version bundled in the APK
            version = "3.8"

            // Try local.properties for buildPython, fall back to common paths
            buildPython(findBuildPython())

            pip {
                // ── Core API server ─────────────────────────────────────────
                install("fastapi==0.104.1")
                install("uvicorn==0.24.0")
                install("pydantic==2.5.2")
                install("python-multipart")
                install("starlette")
                install("anyio")

                // ── LLM providers ────────────────────────────────────────────
                install("openai>=1.6.1")
                install("anthropic")

                // ── Networking / utilities ───────────────────────────────────
                install("requests")
                install("aiohttp")
                install("httpx")
                install("python-dotenv==1.0.0")

                // ── Text-to-Speech (online) ──────────────────────────────────
                install("gTTS")

                // ── Web search ───────────────────────────────────────────────
                install("duckduckgo-search==3.9.6")
                install("trafilatura")
                install("beautifulsoup4")
                install("lxml")

                // ── Numerics (available in Chaquopy ARM registry) ─────────────
                // Used for cosine similarity in memory_manager.py
                install("numpy")

                // NOTE: vosk, sentence-transformers are NOT available via Chaquopy pip.
                // Semantic embeddings are handled by EmbeddingService.kt (onnxruntime-android AAR).
                // STT is handled by Flutter speech_to_text plugin.
            }
        }
    }

    buildTypes {
        release {
            // Signing with debug keys for now; replace with keystore for Play Store
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

dependencies {
    // ── On-device sentence embeddings ───────────────────────────────────────
    // onnxruntime-android: native ARM64/ARMv7 ONNX inference (replaces sentence-transformers pip)
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.17.3")
    // DJL Android tokenizers: Hugging Face WordPiece tokenizer for all-MiniLM-L6-v2
    implementation("ai.djl.android:tokenizers:0.27.0")

    // ── AndroidX / notification support ─────────────────────────────────────
    implementation("androidx.core:core-ktx:1.12.0")
}

flutter {
    source = "../.."
}

// ── Helper: resolve host Python for Chaquopy build steps ────────────────────
fun findBuildPython(): String {
    // 1. Check local.properties for explicit override: buildPython=/path/to/python3
    val propsFile = rootProject.file("local.properties")
    if (propsFile.exists()) {
        val props = java.util.Properties()
        propsFile.inputStream().use { props.load(it) }
        val fromProps = props.getProperty("buildPython")
        if (!fromProps.isNullOrBlank()) return fromProps
    }
    // 2. Fallback candidates
    for (candidate in listOf("/usr/bin/python3", "/usr/local/bin/python3", "python3")) {
        try {
            val result = ProcessBuilder(candidate, "--version").start()
            if (result.waitFor() == 0) return candidate
        } catch (_: Exception) {}
    }
    return "python3"
}
