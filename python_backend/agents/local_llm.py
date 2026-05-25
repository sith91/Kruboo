import os
import threading
from pathlib import Path

class LocalLLM:
    """
    Multi-model local LLM coordinator.
    Supports GPT4All models (Phi-3, Mistral, etc.)
    """
    _gpt4all_models = {}
    _lock = threading.Lock()
    _inference_lock = threading.Lock()

    @classmethod
    def get_gpt4all(cls, model_name):
        # Map nice names to file names
        model_map = {
            "llama-3": "Phi-3-mini-4k-instruct.Q4_0.gguf",
            "mistral": "Phi-3-mini-4k-instruct.Q4_0.gguf", # Forced to Phi-3 for performance and stability
            "phi-3": "Phi-3-mini-4k-instruct.Q4_0.gguf"
        }
        filename = model_map.get(model_name, "Phi-3-mini-4k-instruct.Q4_0.gguf")
        
        with cls._lock:
            if filename not in cls._gpt4all_models:
                try:
                    from gpt4all import GPT4All
                    print(f"Loading GPT4All model: {filename}...")
                    cls._gpt4all_models[filename] = GPT4All(filename, allow_download=False, n_ctx=4096)
                except Exception as e:
                    print(f"Error loading GPT4All ({filename}): {e}")
                    return None
            return cls._gpt4all_models[filename]

    @classmethod
    def generate_response(cls, prompt: str, model_name: str = "llama-3") -> str:
        model = cls.get_gpt4all(model_name)
        if not model: return f"Local model {model_name} offline."
        with cls._inference_lock:
            try:
                return model.generate(prompt, max_tokens=250, temp=0.7).strip()
            except Exception as e: return f"GPT4All Error: {e}"

    @classmethod
    def generate_stream(cls, prompt: str, model_name: str = "llama-3"):
        model = cls.get_gpt4all(model_name)
        if not model:
            yield "Local model offline."
            return
        with cls._inference_lock:
            try:
                for token in model.generate(prompt, max_tokens=300, temp=0.7, streaming=True):
                    yield token
            except Exception as e:
                yield f"Stream Error: {e}"
