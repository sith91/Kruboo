import os
import threading

class LocalLLM:
    """
    A singleton-like wrapper for GPT4All to run a free local LLM entirely within Python.
    Using 'orca-mini-3b' as it is very lightweight (~1.9GB) and runs flawlessly on CPU/Mac.
    """
    _model = None
    _lock = threading.Lock()

    @classmethod
    def get_model(cls):
        with cls._lock:
            if cls._model is None:
                try:
                    from gpt4all import GPT4All
                    # Switching to Phi-3 Mini: Ultra-light (~2GB) but highly intelligent!
                    print("Loading Phi-3 Mini (Optimized Local Brain)...")
                    cls._model = GPT4All("Phi-3-mini-4k-instruct.Q4_0.gguf")
                except ImportError:
                    print("Error: 'gpt4all' library is not installed.")
                    return None
            return cls._model

    @classmethod
    def generate_response(cls, prompt: str) -> str:
        model = cls.get_model()
        if not model:
            return "Local AI pipeline offline."
            
        try:
            output = model.generate(prompt, max_tokens=250, temp=0.7)
            return output.strip()
        except Exception as e:
            return f"Inference Error: {e}"

    @classmethod
    def generate_stream(cls, prompt: str):
        """
        A generator for real-time token streaming.
        """
        model = cls.get_model()
        if not model:
            yield "Local AI pipeline offline."
            return
            
        try:
            # model.generate returns an iterator when streaming=True
            token_generator = model.generate(prompt, max_tokens=300, temp=0.7, streaming=True)
            for token in token_generator:
                yield token
        except Exception as e:
            yield f"Stream Error: {e}"
