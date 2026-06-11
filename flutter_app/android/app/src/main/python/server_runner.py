"""
server_runner.py — Chaquopy entry point for Android
Called by BackendService.kt via Python.getInstance().getModule("server_runner")
Starts the FastAPI/uvicorn server on 127.0.0.1:8000 in a daemon thread.
"""

import threading
import sys
import os

_server_thread = None
_started = False


def start_server(files_dir: str = ""):
    """
    Start the Kruuboo FastAPI backend server.
    
    Args:
        files_dir: Android app's getFilesDir() path, so the backend
                   can write memory.db and other files to persistent storage.
    """
    global _server_thread, _started

    if _started:
        return "already_running"

    # Set working directory to where Python source files live
    # Chaquopy puts bundled Python files in a special path accessible via sys.path
    if files_dir:
        os.environ["KRUUBOO_DATA_DIR"] = files_dir

    def _run():
        try:
            import uvicorn
            # main:app refers to main.py → app = FastAPI(...)
            uvicorn.run(
                "main:app",
                host="127.0.0.1",
                port=8000,
                log_level="warning",
                # Use single worker — Android is single-process
                workers=1,
            )
        except Exception as e:
            print(f"[BackendService] uvicorn error: {e}", file=sys.stderr)

    _server_thread = threading.Thread(target=_run, daemon=True, name="kruuboo-backend")
    _server_thread.start()
    _started = True
    return "started"


def stop_server():
    """Graceful shutdown signal (best-effort on Android)."""
    global _started
    _started = False
    # uvicorn doesn't expose a clean stop API when run in a thread;
    # Android will kill the process cleanly when the ForegroundService stops.
    return "stopped"


def is_running() -> bool:
    return _started and _server_thread is not None and _server_thread.is_alive()
