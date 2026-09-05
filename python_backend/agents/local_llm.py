import os
import sys
import json
import threading
import subprocess
from pathlib import Path

# Force CPU-only for llama-cpp fallback
os.environ["LLAMA_NO_METAL"] = "1"
os.environ["GGML_NO_METAL"] = "1"

# ── Paths ────────────────────────────────────────────────────────────────────
LITERT_MODEL_DIR = os.path.expanduser("~/.cache/litert-lm")
LITERT_MODEL_PATH = os.path.join(LITERT_MODEL_DIR, "gemma-4-E2B-it.litertlm")
LITERT_VENV_PYTHON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "venv_litert", "bin", "python3"
)
LITERT_SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "litert_server.py")

# Legacy GGUF paths (fallback)
DEFAULT_MODEL_PATH = str(Path.home() / ".cache" / "gpt4all" / "Phi-3-mini-4k-instruct.Q4_0.gguf")
FALLBACK_MODEL_PATH = str(Path.home() / ".cache" / "gpt4all" / "mistral-7b-instruct-v0.1.Q4_0.gguf")

# ── Which engine is active ──────────────────────────────────────────────────
_ENGINE_LITERT = "litert"
_ENGINE_LLAMACPP = "llamacpp"
_ENGINE_OFFLINE = "offline"


class LocalLLM:
    """
    Local LLM with two backends:
      1. LiteRT-LM (Gemma 4 E2B, via Python 3.11 subprocess) — preferred
      2. llama-cpp-python (Phi-3/Mistral GGUF, in-process CPU) — fallback
    """
    _engine_type = None
    _lock = threading.Lock()
    _inference_lock = threading.Lock()

    # -- LiteRT subprocess state --
    _litert_process = None
    _litert_ready = False

    # -- llama-cpp state --
    _llama_model = None

    @classmethod
    def _detect_engine(cls):
        """Determine which engine to use."""
        if cls._engine_type is not None:
            return cls._engine_type

        # 1. Try LiteRT-LM
        if os.path.exists(LITERT_MODEL_PATH) and os.path.exists(LITERT_VENV_PYTHON):
            cls._engine_type = _ENGINE_LITERT
            print(f"[LocalLLM] Using LiteRT-LM engine (Gemma 4 E2B)")
            return cls._engine_type

        # 2. Try llama-cpp
        gguf_path = DEFAULT_MODEL_PATH if os.path.exists(DEFAULT_MODEL_PATH) else \
                    FALLBACK_MODEL_PATH if os.path.exists(FALLBACK_MODEL_PATH) else None
        if gguf_path:
            cls._engine_type = _ENGINE_LLAMACPP
            print(f"[LocalLLM] Using llama-cpp fallback ({os.path.basename(gguf_path)})")
            return cls._engine_type

        cls._engine_type = _ENGINE_OFFLINE
        print("[LocalLLM] No local model available. LLM will be offline.")
        return cls._engine_type

    # ═══════════════════════════════════════════════════════════════════════
    # LiteRT-LM Subprocess Management
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    def _ensure_litert_process(cls):
        """Start the LiteRT subprocess if not already running."""
        if cls._litert_process is not None and cls._litert_process.poll() is None:
            return True  # Already running

        try:
            print(f"[LocalLLM] Starting LiteRT-LM subprocess...")
            cls._litert_process = subprocess.Popen(
                [LITERT_VENV_PYTHON, LITERT_SERVER_SCRIPT, LITERT_MODEL_PATH],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line-buffered
            )

            # Wait for "ready" message
            for _ in range(60):  # Up to 60 lines of output waiting for ready
                line = cls._litert_process.stdout.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.strip())
                    if msg.get("type") == "ready":
                        cls._litert_ready = True
                        print(f"[LocalLLM] LiteRT-LM subprocess ready: {msg.get('message')}")
                        return True
                    elif msg.get("type") == "error":
                        print(f"[LocalLLM] LiteRT-LM error: {msg.get('message')}")
                        cls._kill_litert()
                        return False
                    elif msg.get("type") == "status":
                        print(f"[LocalLLM] LiteRT-LM: {msg.get('message')}")
                except json.JSONDecodeError:
                    continue

            print("[LocalLLM] LiteRT-LM subprocess failed to become ready")
            cls._kill_litert()
            return False

        except Exception as e:
            print(f"[LocalLLM] Failed to start LiteRT subprocess: {e}")
            cls._litert_process = None
            return False

    @classmethod
    def _kill_litert(cls):
        """Kill the LiteRT subprocess."""
        if cls._litert_process:
            try:
                cls._litert_process.kill()
            except:
                pass
            cls._litert_process = None
            cls._litert_ready = False

    @classmethod
    def _litert_send(cls, msg):
        """Send a JSON message to the LiteRT subprocess."""
        if cls._litert_process and cls._litert_process.poll() is None:
            cls._litert_process.stdin.write(json.dumps(msg) + "\n")
            cls._litert_process.stdin.flush()

    @classmethod
    def _litert_read_line(cls):
        """Read a single JSON response line from the LiteRT subprocess."""
        if cls._litert_process and cls._litert_process.poll() is None:
            line = cls._litert_process.stdout.readline()
            if line:
                try:
                    return json.loads(line.strip())
                except json.JSONDecodeError:
                    return None
        return None

    # ═══════════════════════════════════════════════════════════════════════
    # llama-cpp Fallback
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    def _get_llama_model(cls):
        """Load the llama-cpp-python model (lazy, singleton)."""
        if cls._llama_model is not None:
            return cls._llama_model

        model_path = DEFAULT_MODEL_PATH if os.path.exists(DEFAULT_MODEL_PATH) else \
                     FALLBACK_MODEL_PATH if os.path.exists(FALLBACK_MODEL_PATH) else None

        if not model_path:
            return None

        try:
            from llama_cpp import Llama
            print(f"[LocalLLM] Loading {os.path.basename(model_path)} (CPU-only)...")
            cpu_cores = os.cpu_count() or 4
            optimal_threads = max(4, cpu_cores - 2 if cpu_cores > 4 else cpu_cores)

            cls._llama_model = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_threads=optimal_threads,
                n_gpu_layers=0,
                verbose=False,
            )
            print(f"[LocalLLM] Model loaded: {os.path.basename(model_path)}")
        except Exception as e:
            print(f"[LocalLLM] Failed to load llama-cpp model: {e}")
            cls._llama_model = None

        return cls._llama_model

    # ═══════════════════════════════════════════════════════════════════════
    # Public API (same interface as before)
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    def generate_response(cls, prompt, model_name="gemma"):
        """Generate a full response (non-streaming)."""
        with cls._lock:
            engine = cls._detect_engine()

        if engine == _ENGINE_OFFLINE:
            return "I'm running in offline mode. Please configure an API key in Settings for full AI responses."

        # Collect streamed tokens into a single string
        tokens = list(cls.generate_stream(prompt, model_name))
        return "".join(tokens)

    @classmethod
    def generate_stream(cls, prompt, model_name="gemma"):
        """Generate a streaming response (yields token strings)."""
        with cls._lock:
            engine = cls._detect_engine()

        if engine == _ENGINE_OFFLINE:
            yield "I'm running in offline mode. Please configure an API key in Settings for full AI responses."
            return

        if engine == _ENGINE_LITERT:
            yield from cls._litert_stream(prompt)
        else:
            yield from cls._llamacpp_stream(prompt)

    @classmethod
    def _litert_stream(cls, prompt):
        """Stream tokens from LiteRT-LM subprocess."""
        with cls._inference_lock:
            if not cls._ensure_litert_process():
                # Fallback to llama-cpp if LiteRT fails to start
                print("[LocalLLM] LiteRT failed, falling back to llama-cpp")
                cls._engine_type = _ENGINE_LLAMACPP
                yield from cls._llamacpp_stream(prompt)
                return

            # Extract system prompt from the prompt if it's formatted
            # The prompt from assistant.py is already formatted with system/user markers
            cls._litert_send({
                "type": "generate",
                "prompt": prompt,
                "system": "",
                "max_tokens": 512,
            })

            # Read tokens until "done"
            while True:
                msg = cls._litert_read_line()
                if msg is None:
                    # Process died or EOF
                    cls._kill_litert()
                    yield "[LiteRT-LM process terminated unexpectedly]"
                    return

                msg_type = msg.get("type")
                if msg_type == "token":
                    text = msg.get("text", "")
                    if text:
                        yield text
                elif msg_type == "done":
                    return
                elif msg_type == "error":
                    yield f"[LLM Error: {msg.get('message', 'unknown')}]"
                    return

    @classmethod
    def _llamacpp_stream(cls, prompt):
        """Stream tokens from llama-cpp-python (fallback)."""
        model = cls._get_llama_model()
        if not model:
            yield "I'm running in offline mode. Please configure an API key in Settings for full AI responses."
            return
        with cls._inference_lock:
            try:
                for chunk in model(
                    prompt,
                    max_tokens=512,
                    stop=["<|user|>", "<|end|>", "<|system|>", "User:", "user:", "Assistant:", "assistant:"],
                    stream=True,
                    echo=False,
                ):
                    token = chunk["choices"][0]["text"]
                    if token:
                        yield token
            except Exception as e:
                yield f"Stream Error: {e}"

    @classmethod
    def get_engine_info(cls):
        """Return info about which engine is active."""
        with cls._lock:
            engine = cls._detect_engine()
        return {
            "engine": engine,
            "litert_available": os.path.exists(LITERT_MODEL_PATH),
            "litert_venv_available": os.path.exists(LITERT_VENV_PYTHON),
            "gguf_available": os.path.exists(DEFAULT_MODEL_PATH) or os.path.exists(FALLBACK_MODEL_PATH),
        }
