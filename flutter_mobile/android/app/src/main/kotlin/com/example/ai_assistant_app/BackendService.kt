package com.example.ai_assistant_app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.content.pm.ServiceInfo
import android.os.PowerManager
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.os.Bundle
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject
import java.io.OutputStreamWriter
import androidx.core.app.NotificationCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.util.concurrent.Executors
import android.media.projection.MediaProjectionManager
import android.media.projection.MediaProjection
import android.hardware.display.VirtualDisplay
import android.hardware.display.DisplayManager
import android.media.ImageReader
import android.graphics.PixelFormat
import android.graphics.Bitmap
import android.util.Base64
import java.io.ByteArrayOutputStream
import android.util.DisplayMetrics
import android.view.WindowManager
import android.content.Context

/**
 * BackendService — Android ForegroundService that runs the Kruuboo Python
 * FastAPI server on 127.0.0.1:8000 using Chaquopy (embedded CPython).
 *
 * Lifecycle:
 *  - Started by MainActivity via MethodChannel("com.kruuboo/backend") → startBackend
 *  - Stopped automatically when the app is killed
 */
class BackendService : Service() {

    companion object {
        private const val TAG = "KruubooBackend"
        private const val CHANNEL_ID = "kruuboo_backend_channel"
        private const val NOTIFICATION_ID = 1001
        private const val ACTION_START = "START_BACKEND"
        private const val ACTION_STOP  = "STOP_BACKEND"
        private const val ACTION_START_LISTENING = "START_LISTENING"
        private const val ACTION_STOP_LISTENING = "STOP_LISTENING"

        @Volatile
        var isRunning = false

        @Volatile
        var instance: BackendService? = null

        @Volatile
        var screenCaptureResultCode: Int = 0

        @Volatile
        var screenCaptureIntentData: Intent? = null

        @JvmStatic
        fun getScreenCaptureBase64(): String? {
            val inst = instance
            if (inst == null) {
                Log.e(TAG, "BackendService instance is not running")
                return null
            }
            return inst.captureScreenToBase64()
        }
    }

    private val executor = Executors.newSingleThreadExecutor()
    private var wakeLock: PowerManager.WakeLock? = null
    private var speechRecognizer: SpeechRecognizer? = null
    private var tts: TextToSpeech? = null
    private var isListeningEnabled = false

    // ──────────────────────────────────────────────────────────────────────────
    // Service lifecycle
    // ──────────────────────────────────────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        isRunning = true
        instance = this

        // Acquire WakeLock to keep the Python server active when screen is off
        try {
            val powerManager = getSystemService(POWER_SERVICE) as PowerManager
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Kruuboo::BackendWakeLock").apply {
                acquire()
            }
            Log.i(TAG, "WakeLock acquired")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to acquire WakeLock: ${e.message}")
        }

        createNotificationChannel()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                NOTIFICATION_ID,
                buildNotification(),
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            )
        } else {
            startForeground(NOTIFICATION_ID, buildNotification())
        }

        // Initialize TTS
        try {
            tts = TextToSpeech(this) { status ->
                if (status == TextToSpeech.SUCCESS) {
                    tts?.language = java.util.Locale.US
                    Log.i(TAG, "TextToSpeech initialized successfully")
                } else {
                    Log.e(TAG, "Failed to initialize TextToSpeech: status = $status")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exception initializing TextToSpeech: ${e.message}")
        }

        Log.i(TAG, "BackendService created — initializing EmbeddingService...")
        EmbeddingService.initialize(assets)
        Log.i(TAG, "Initializing Chaquopy...")
        initPython()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                Log.i(TAG, "Stop requested — shutting down backend service")
                stopSelf()
            }
            ACTION_START_LISTENING -> {
                Log.i(TAG, "Start listening requested")
                isListeningEnabled = true
                startSpeechListening()
            }
            ACTION_STOP_LISTENING -> {
                Log.i(TAG, "Stop listening requested")
                isListeningEnabled = false
                stopSpeechListening()
            }
            else -> {
                // Default / ACTION_START
                Log.i(TAG, "Start requested — launching Python backend")
                launchPythonBackend()
            }
        }
        return START_STICKY   // Restart service if killed by system
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        isRunning = false
        instance = null
        isListeningEnabled = false
        stopSpeechListening()
        stopPythonBackend()
        executor.shutdownNow()

        // Shutdown TTS
        try {
            tts?.stop()
            tts?.shutdown()
            tts = null
            Log.i(TAG, "TextToSpeech released")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to release TextToSpeech: ${e.message}")
        }

        // Release WakeLock
        try {
            wakeLock?.let {
                if (it.isHeld) {
                    it.release()
                    Log.i(TAG, "WakeLock released")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to release WakeLock: ${e.message}")
        }
        Log.i(TAG, "BackendService destroyed")
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Chaquopy / Python bridge
    // ──────────────────────────────────────────────────────────────────────────

    private fun initPython() {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
            Log.i(TAG, "Chaquopy Python started successfully")
        }
    }

    private fun launchPythonBackend() {
        executor.submit {
            try {
                val py = Python.getInstance()
                val runner = py.getModule("server_runner")

                // Pass Android file storage directory so the backend can persist data
                val filesDir = this.filesDir.absolutePath
                Log.i(TAG, "Starting FastAPI backend — data dir: $filesDir")

                val result = runner.callAttr("start_server", filesDir).toString()
                Log.i(TAG, "Backend launch result: $result")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to start Python backend: ${e.message}", e)
                updateNotificationError("Failed to start backend: ${e.message}")
            }
        }
    }

    private fun stopPythonBackend() {
        try {
            if (Python.isStarted()) {
                val py = Python.getInstance()
                py.getModule("server_runner").callAttr("stop_server")
                Log.i(TAG, "Python backend stopped")
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error stopping Python backend: ${e.message}")
        }
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Notification (required for ForegroundService on Android 8+)
    // ──────────────────────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Kruuboo AI Backend",
                NotificationManager.IMPORTANCE_LOW  // Silent — no sound/vibration
            ).apply {
                description = "Keeps the Kruuboo AI brain running in the background"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(contentText: String = "AI backend active on 127.0.0.1:8000"): Notification {
        val notificationIntent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            notificationIntent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Kruuboo is running")
            .setContentText(contentText)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .build()
    }

    private fun updateNotificationError(errorMsg: String) {
        val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(NOTIFICATION_ID, buildNotification(errorMsg))
    }

    // ──────────────────────────────────────────────────────────────────────────
    // Background Speech & TTS Logic
    // ──────────────────────────────────────────────────────────────────────────

    private fun startSpeechListening() {
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            try {
                if (speechRecognizer == null) {
                    speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this)
                    speechRecognizer?.setRecognitionListener(object : RecognitionListener {
                        override fun onReadyForSpeech(params: Bundle?) {
                            Log.d(TAG, "Ready for speech in background")
                        }
                        override fun onBeginningOfSpeech() {}
                        override fun onRmsChanged(rmsdB: Float) {}
                        override fun onBufferReceived(buffer: ByteArray?) {}
                        override fun onEndOfSpeech() {}
                        override fun onError(error: Int) {
                            Log.d(TAG, "SpeechRecognizer error: $error")
                            if (isListeningEnabled) {
                                restartListeningDelayed()
                            }
                        }
                        override fun onResults(results: Bundle?) {
                            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                            if (matches != null && matches.isNotEmpty()) {
                                val text = matches[0]
                                Log.i(TAG, "Speech recognized in background: $text")
                                handleSpeechInput(text)
                            }
                            if (isListeningEnabled) {
                                restartListeningDelayed()
                            }
                        }
                        override fun onPartialResults(partialResults: Bundle?) {}
                        override fun onEvent(eventType: Int, params: Bundle?) {}
                    })
                }

                val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
                }
                speechRecognizer?.startListening(intent)
                Log.i(TAG, "Started background speech recognition")
            } catch (e: Exception) {
                Log.e(TAG, "Failed starting SpeechRecognizer: ${e.message}")
            }
        }
    }

    private fun stopSpeechListening() {
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            try {
                speechRecognizer?.stopListening()
                speechRecognizer?.cancel()
                speechRecognizer?.destroy()
                speechRecognizer = null
                Log.i(TAG, "Stopped background speech recognition")
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping SpeechRecognizer: ${e.message}")
            }
        }
    }

    private fun restartListeningDelayed() {
        android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
            if (isListeningEnabled) {
                startSpeechListening()
            }
        }, 1000)
    }

    private fun handleSpeechInput(text: String) {
        val lowerText = text.lowercase()
        val wakeWords = listOf("kruuboo", "kruboo", "assistant")
        var foundWakeWord: String? = null
        for (w in wakeWords) {
            if (lowerText.contains(w)) {
                foundWakeWord = w
                break
            }
        }

        if (foundWakeWord != null) {
            Log.i(TAG, "Wake word matched: $foundWakeWord")
            val index = lowerText.indexOf(foundWakeWord)
            val queryText = text.substring(index + foundWakeWord.length).trim().replace(Regex("^[,\\s.?!]+"), "")
            
            if (queryText.isEmpty()) {
                speakText("Yes, I am listening.")
            } else {
                sendQueryToBackend(queryText)
            }
        }
    }

    private fun sendQueryToBackend(queryText: String) {
        executor.submit {
            var connection: HttpURLConnection? = null
            try {
                val url = URL("http://127.0.0.1:8000/query")
                connection = url.openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true

                val jsonInput = JSONObject().apply {
                    put("query", queryText)
                    put("is_voice", true)
                    put("language", "English")
                    put("assistant_name", "Kruuboo")
                    put("llm_provider", "local")
                    put("llm_model", "llama-3")
                    put("api_key", "")
                    put("allow_web_search", true)
                }

                OutputStreamWriter(connection.outputStream).use { writer ->
                    writer.write(jsonInput.toString())
                    writer.flush()
                }

                val responseCode = connection.responseCode
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    val responseStr = connection.inputStream.bufferedReader().use { it.readText() }
                    val responseJson = JSONObject(responseStr)
                    val responseText = responseJson.optString("response", "")
                    Log.i(TAG, "Backend Response: $responseText")
                    if (responseText.isNotEmpty()) {
                        speakText(responseText)
                    }
                } else {
                    Log.e(TAG, "Error query status: $responseCode")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to query backend: ${e.message}", e)
            } finally {
                connection?.disconnect()
            }
        }
    }

    private fun speakText(text: String) {
        android.os.Handler(android.os.Looper.getMainLooper()).post {
            try {
                if (isListeningEnabled) {
                    speechRecognizer?.stopListening()
                    speechRecognizer?.cancel()
                }

                val params = Bundle().apply {
                    putString(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, "background_tts")
                }
                tts?.setOnUtteranceProgressListener(object : android.speech.tts.UtteranceProgressListener() {
                    override fun onStart(utteranceId: String?) {}
                    override fun onDone(utteranceId: String?) {
                        if (isListeningEnabled) {
                            startSpeechListening()
                        }
                    }
                    override fun onError(utteranceId: String?) {
                        if (isListeningEnabled) {
                            startSpeechListening()
                        }
                    }
                })

                tts?.speak(text, TextToSpeech.QUEUE_FLUSH, params, "background_tts")
            } catch (e: Exception) {
                Log.e(TAG, "Error speaking text: ${e.message}")
                if (isListeningEnabled) {
                    startSpeechListening()
                }
            }
        }
    }
    fun captureScreenToBase64(): String? {
        val resultCode = screenCaptureResultCode
        val intentData = screenCaptureIntentData
        if (intentData == null) {
            Log.e(TAG, "No screen capture intent data available. Did the user grant permission?")
            return null
        }

        val mpManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        var mediaProjection: MediaProjection? = null
        var virtualDisplay: VirtualDisplay? = null
        var imageReader: ImageReader? = null
        try {
            mediaProjection = mpManager.getMediaProjection(resultCode, intentData)
            if (mediaProjection == null) {
                Log.e(TAG, "Failed to obtain MediaProjection")
                return null
            }

            // Get display metrics
            val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val metrics = DisplayMetrics()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val bounds = windowManager.currentWindowMetrics.bounds
                metrics.widthPixels = bounds.width()
                metrics.heightPixels = bounds.height()
                metrics.densityDpi = DisplayMetrics.DENSITY_DEFAULT
            } else {
                windowManager.defaultDisplay.getMetrics(metrics)
            }

            // Downscale to 480p width to optimize size for Gemini
            val width = 480
            val height = (metrics.heightPixels.toFloat() / metrics.widthPixels.toFloat() * width).toInt()

            imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
            
            virtualDisplay = mediaProjection.createVirtualDisplay(
                "KruubooScreenCapture",
                width,
                height,
                DisplayMetrics.DENSITY_DEFAULT,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.surface,
                null,
                null
            )

            // Brief wait for VirtualDisplay connection and frame acquisition
            Thread.sleep(800)

            val image = imageReader.acquireLatestImage()
            if (image == null) {
                Log.e(TAG, "Acquired image is null")
                return null
            }

            val planes = image.planes
            val buffer = planes[0].buffer
            val pixelStride = planes[0].pixelStride
            val rowStride = planes[0].rowStride
            val rowPadding = rowStride - pixelStride * width

            val bitmap = Bitmap.createBitmap(width + rowPadding / pixelStride, height, Bitmap.Config.ARGB_8888)
            bitmap.copyPixelsFromBuffer(buffer)
            image.close()

            val croppedBitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height)
            bitmap.recycle()

            val outputStream = ByteArrayOutputStream()
            croppedBitmap.compress(Bitmap.CompressFormat.JPEG, 70, outputStream)
            val bytes = outputStream.toByteArray()
            croppedBitmap.recycle()

            return Base64.encodeToString(bytes, Base64.NO_WRAP)
        } catch (e: Exception) {
            Log.e(TAG, "Error during screen capture: ${e.message}", e)
            return null
        } finally {
            virtualDisplay?.release()
            imageReader?.close()
            mediaProjection?.stop()
        }
    }
}
