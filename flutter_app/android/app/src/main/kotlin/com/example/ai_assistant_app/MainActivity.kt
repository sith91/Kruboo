package com.example.ai_assistant_app

import android.content.Intent
import android.os.Build
import android.util.Log
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    companion object {
        private const val TAG = "KruubooMain"
        // Must match the channel name used in lib/main.dart
        private const val BACKEND_CHANNEL = "com.kruuboo/backend"
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // Initialize embedding service with asset manager early
        EmbeddingService.initialize(assets)

        // ── Flutter ↔ Kotlin MethodChannel ──────────────────────────────────
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            BACKEND_CHANNEL
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "startBackend" -> {
                    Log.i(TAG, "Flutter requested: startBackend")
                    startBackendService()
                    result.success("Backend service started")
                }
                "stopBackend" -> {
                    Log.i(TAG, "Flutter requested: stopBackend")
                    stopBackendService()
                    result.success("Backend service stopped")
                }
                "backendStatus" -> {
                    result.success(BackendService.isRunning)
                }
                "getEmbedding" -> {
                    val text = call.argument<String>("text")
                    if (text != null) {
                        val emb = EmbeddingService.embed(text)
                        if (emb != null) {
                            result.success(emb)
                        } else {
                            result.error("EMBEDDING_FAILED", "Failed to generate embedding", null)
                        }
                    } else {
                        result.error("BAD_ARGS", "Missing 'text' argument", null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    private fun startBackendService() {
        val intent = Intent(this, BackendService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopBackendService() {
        val intent = Intent(this, BackendService::class.java)
        stopService(intent)
    }
}

