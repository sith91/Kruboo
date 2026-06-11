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
import androidx.core.app.NotificationCompat
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import java.util.concurrent.Executors

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

        @Volatile
        var isRunning = false
    }

    private val executor = Executors.newSingleThreadExecutor()

    // ──────────────────────────────────────────────────────────────────────────
    // Service lifecycle
    // ──────────────────────────────────────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        isRunning = true
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
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
        stopPythonBackend()
        executor.shutdownNow()
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
}
