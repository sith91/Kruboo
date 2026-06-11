import os
import threading
from pathlib import Path

# Force CPU-only — llama-cpp-python is built without Metal, so no SIGABRT
# These are also set here as a belt-and-suspenders measure
os.environ["LLAMA_NO_METAL"] = "1"
os.environ["GGML_NO_METAL"] = "1"

DEFAULT_MODEL_PATH = str(Path.home() / ".cache" / "gpt4all" / "Phi-3-mini-4k-instruct.Q4_0.gguf")
FALLBACK_MODEL_PATH = str(Path.home() / ".cache" / "gpt4all" / "mistral-7b-instruct-v0.1.Q4_0.gguf")

class LocalLLM:
    """
    CPU-only local LLM using llama-cpp-python (compiled without Metal).
    Falls back to an offline message if the model cannot load.
    """
    _model = None
    _model_path = None
    _lock = threading.Lock()
    _inference_lock = threading.Lock()

    @classmethod
    def get_model(cls):
        with cls._lock:
            if cls._model is not None:
                return cls._model

            # Pick best available model
            model_path = DEFAULT_MODEL_PATH if os.path.exists(DEFAULT_MODEL_PATH) else \
                         FALLBACK_MODEL_PATH if os.path.exists(FALLBACK_MODEL_PATH) else None

            if not model_path:
                print("[LocalLLM] No GGUF model found. LLM will be offline.")
                return None

            try:
                from llama_cpp import Llama
                print(f"[LocalLLM] Loading {os.path.basename(model_path)} (CPU-only)...")
                cls._model = Llama(
                    model_path=model_path,
                    n_ctx=512,          # Small context fits in CPU RAM without crashing
                    n_threads=4,        # Use 4 CPU threads
                    n_gpu_layers=0,     # CPU ONLY — no Metal/GPU
                    verbose=False,
                )
                cls._model_path = model_path
                print(f"[LocalLLM] Model loaded: {os.path.basename(model_path)}")
            except Exception as e:
                print(f"[LocalLLM] Failed to load model: {e}")
                cls._model = None

            return cls._model

    @classmethod
    def generate_response(cls, prompt: str, model_name: str = "llama-3") -> str:
        model = cls.get_model()
        if not model:
            return "I'm running in offline mode. Please configure an API key in Settings for full AI responses."
        with cls._inference_lock:
            try:
                result = model(prompt, max_tokens=150, stop=["<|user|>", "<|end|>", "User:", "\n\n"], echo=False)
                return result["choices"][0]["text"].strip()
            except Exception as e:
                return f"LLM Error: {e}"

    @classmethod
    def generate_stream(cls, prompt: str, model_name: str = "llama-3"):
        model = cls.get_model()
        if not model:
            yield "I'm running in offline mode. Please configure an API key in Settings for full AI responses."
            return
        with cls._inference_lock:
            try:
                for chunk in model(
                    prompt,
                    max_tokens=150,
                    stop=["<|user|>", "<|end|>", "User:", "\n\n"],
                    stream=True,
                    echo=False,
                ):
                    token = chunk["choices"][0]["text"]
                    if token:
                        yield token
            except Exception as e:
                yield f"Stream Error: {e}"
