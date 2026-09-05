"""
server_runner.py — Chaquopy entry point for Android
Called by BackendService.kt via Python.getInstance().getModule("server_runner")
Starts the FastAPI/uvicorn server dynamically on a free port in a daemon thread.
"""

import threading
import sys
import os
import socket

_server_thread = None
_started = False
_assigned_port = 8000


def get_free_port(start_port: int = 8000) -> int:
    """Find a free TCP port on localhost starting from start_port."""
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            port += 1
    return start_port


def start_server(files_dir: str = "") -> int:
    """
    Start the Kruuboo FastAPI backend server on a free port.
    
    Args:
        files_dir: Android app's getFilesDir() path, so the backend
                   can write memory.db and other files to persistent storage.
                   
    Returns:
        The integer port the server was started on.
    """
    global _server_thread, _started, _assigned_port

    if _started and _server_thread is not None and _server_thread.is_alive():
        return _assigned_port

    if files_dir:
        os.environ["KRUUBOO_DATA_DIR"] = files_dir

    _assigned_port = get_free_port(8000)
    os.environ["PORT"] = str(_assigned_port)

    def _run():
        try:
            import uvicorn
            uvicorn.run(
                "main:app",
                host="127.0.0.1",
                port=_assigned_port,
                log_level="warning",
                workers=1,
            )
        except Exception as e:
            print(f"[BackendService] uvicorn error on port {_assigned_port}: {e}", file=sys.stderr)

    _server_thread = threading.Thread(target=_run, daemon=True, name="kruuboo-backend")
    _server_thread.start()
    _started = True
    return _assigned_port


def get_server_port() -> int:
    """Returns the dynamically assigned server port."""
    global _assigned_port
    return _assigned_port


def stop_server():
    """Graceful shutdown signal (best-effort on Android)."""
    global _started
    _started = False
    return "stopped"


def is_running() -> bool:
    return _started and _server_thread is not None and _server_thread.is_alive()
