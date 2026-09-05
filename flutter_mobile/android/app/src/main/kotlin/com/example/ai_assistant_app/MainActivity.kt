package com.example.ai_assistant_app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import android.content.Context
import android.media.projection.MediaProjectionManager
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.objects.ObjectDetection
import com.google.mlkit.vision.objects.defaults.ObjectDetectorOptions
import com.google.android.gms.tasks.Tasks
import android.graphics.BitmapFactory
import android.util.Base64
import java.util.concurrent.Executors

class MainActivity : FlutterActivity() {

    companion object {
        private const val TAG = "KruubooMain"
        // Must match the channel name used in lib/main.dart
        private const val BACKEND_CHANNEL = "com.kruuboo/backend"
        private const val SCREEN_CAPTURE_REQUEST_CODE = 1002
    }

    private var pendingResult: MethodChannel.Result? = null
    private val executor = Executors.newSingleThreadExecutor()

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
                    result.success(BackendService.backendPort)
                }
                "getBackendPort" -> {
                    result.success(BackendService.backendPort)
                }
                "stopBackend" -> {
                    Log.i(TAG, "Flutter requested: stopBackend")
                    stopBackendService()
                    result.success("Backend service stopped")
                }
                "backendStatus" -> {
                    result.success(BackendService.isRunning)
                }
                "enableBackgroundListening" -> {
                    val enabled = call.argument<Boolean>("enabled") ?: false
                    Log.i(TAG, "Flutter requested: enableBackgroundListening = $enabled")
                    if (enabled) {
                        requestPermissionsForBackgroundListening()
                    }
                    toggleBackgroundListening(enabled)
                    result.success("OK")
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
                "requestScreenCapture" -> {
                    Log.i(TAG, "Flutter requested: requestScreenCapture")
                    pendingResult = result
                    val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                    startActivityForResult(mediaProjectionManager.createScreenCaptureIntent(), SCREEN_CAPTURE_REQUEST_CODE)
                }
                "hasScreenCapturePermission" -> {
                    result.success(BackendService.screenCaptureIntentData != null)
                }
                "detectObjects" -> {
                    val base64Image = call.argument<String>("image")
                    if (base64Image != null) {
                        executor.submit {
                            val resultText = detectObjects(base64Image)
                            runOnUiThread {
                                result.success(resultText)
                            }
                        }
                    } else {
                        result.error("BAD_ARGS", "Missing 'image' argument", null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == SCREEN_CAPTURE_REQUEST_CODE) {
            if (resultCode == RESULT_OK && data != null) {
                BackendService.screenCaptureResultCode = resultCode
                BackendService.screenCaptureIntentData = data
                Log.i(TAG, "Screen capture permission granted")
                pendingResult?.success(true)
            } else {
                Log.e(TAG, "Screen capture permission denied")
                pendingResult?.success(false)
            }
            pendingResult = null
        }
    }

    private fun startBackendService() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    101
                )
            }
        }
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

    private fun requestPermissionsForBackgroundListening() {
        val permissions = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.RECORD_AUDIO)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
        if (permissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissions.toTypedArray(), 101)
        }
    }

    private fun toggleBackgroundListening(enabled: Boolean) {
        val intent = Intent(this, BackendService::class.java).apply {
            action = if (enabled) "START_LISTENING" else "STOP_LISTENING"
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun detectObjects(base64Image: String): String {
        try {
            val decodedString = Base64.decode(base64Image, Base64.DEFAULT)
            val bitmap = BitmapFactory.decodeByteArray(decodedString, 0, decodedString.size)
            val image = InputImage.fromBitmap(bitmap, 0)
            
            val options = ObjectDetectorOptions.Builder()
                .setDetectorMode(ObjectDetectorOptions.SINGLE_IMAGE_MODE)
                .enableMultipleObjects()
                .enableClassification()
                .build()
                
            val objectDetector = ObjectDetection.getClient(options)
            val result = Tasks.await(objectDetector.process(image))
            
            if (result.isEmpty()) {
                return "No objects detected in the image."
            }
            
            val detected = mutableListOf<String>()
            for (obj in result) {
                val labels = obj.labels
                if (labels.isNotEmpty()) {
                    for (label in labels) {
                        detected.add(label.text)
                    }
                } else {
                    detected.add("unknown object")
                }
            }
            
            val grouped = detected.groupBy { it }.map { "${it.value.size} ${it.key}" }
            return "I detected: ${grouped.joinToString(", ")}."
        } catch (e: Exception) {
            Log.e("ObjectDetection", "Error detecting objects: ${e.message}", e)
            return "Failed to run local object detection: ${e.message}"
        }
    }
}

