# Python 3.9 Dependency Compatibility Guide

This document details a critical compatibility issue encountered when running the Kruuboo Python backend under Python 3.9 (such as the default macOS Python 3.9.6 runtime), the root cause, and the resolution implemented in the dependency configuration.

---

## 1. The Symptom: Startup Import Crash
When attempting to start the Python FastAPI backend or execute any script importing the assistant modules, the process crashes immediately on import with the following traceback:

```text
Traceback (most recent call last):
  File "python_backend/main.py", line 4, in <module>
    from agents.assistant import handle_user_query, stream_user_query, ...
  File "python_backend/agents/assistant.py", line 10, in <module>
    from tools.memory_manager import MemoryManager
  File "python_backend/tools/memory_manager.py", line 6, in <module>
    from sentence_transformers import SentenceTransformer
  File "python_backend/venv/lib/python3.9/site-packages/sentence_transformers/__init__.py", line 15, in <module>
    from sentence_transformers.cross_encoder import (
  ...
  File "python_backend/venv/lib/python3.9/site-packages/transformers/data/data_collator.py", line 1233, in DataCollatorForLanguageModeling
    offsets: np.ndarray[np.ndarray[tuple[int, int]]], special_tokens_mask: np.ndarray[np.ndarray[int]]
TypeError: Too few arguments for numpy.ndarray
```

---

## 2. Root Cause Analysis
The issue stems from a combination of NumPy's generic typing implementation, Python 3.9's type-hint evaluator, and the Hugging Face `transformers` library code:

1. **NumPy Subscripting Limitations:** In NumPy version `1.22.x` and other versions running under Python 3.9, generic class-level subscripting on `numpy.ndarray` (e.g. `np.ndarray[type]`) is strictly constrained. It only accepts basic parameters (like `np.ndarray[Any, np.dtype[Any]]`) and throws a `TypeError` if subscripted with nested generics or unexpected arguments.
2. **Generic Typing in Transformers:** In newer versions of the `transformers` library (specifically `transformers >= 4.41.0`), function signature type hints were introduced using nested NumPy generics:
   ```python
   offsets: np.ndarray[np.ndarray[tuple[int, int]]]
   ```
3. **Import-Time Evaluation:** Because these type hints are evaluated at import time when Python reads and parses the module, they trigger `np.ndarray.__class_getitem__` immediately. Under Python 3.9, this triggers the `TypeError: Too few arguments for numpy.ndarray` exception, crashing the entire import chain before any server code can execute.
4. **Default macOS Python:** Since macOS ships with Python 3.9.6 by default, developers launching the backend on a clean macOS environment automatically compile virtual environments using Python 3.9, causing the application to crash on boot.

---

## 3. Resolution & Dependency Constraints
To ensure cross-compatibility with Python 3.9, we must pin dependencies to versions that do not use nested generic type hints on NumPy arrays.

### Package Pins
The following package constraints have been added to [requirements.txt](file:///Users/sithija/.gemini/antigravity/scratch/ai_assistant/python_backend/requirements.txt):
* **`transformers<4.40.0`:** Limits the Hugging Face library to a stable version (e.g. `4.39.3`) where nested NumPy subscripting is not present on signatures, preventing import-time evaluation errors.
* **`sentence-transformers<3.0.0`:** Downgrades the sentence embeddings wrapper to a compatible version (e.g. `2.7.0`) since `sentence-transformers >= 3.0.0` strictly requires `transformers >= 4.41.0`.

### Requirements File Fragment
The relevant section in the requirements file has been locked as follows:
```text
google-search-results==2.4.2
sentence-transformers<3.0.0
transformers<4.40.0
numpy
scikit-learn
```

---

## 4. Verification
You can verify the environment's integrity by executing the local verification script inside the Python virtual environment:
```bash
# From project root
python_backend/venv/bin/python <appDataDir>/brain/<conversation-id>/scratch/verify_desktop_memory.py
```
If the environment is configured correctly, the imports will succeed without raising `TypeError`, and the console will output:
`SUCCESS: All memory tests passed locally!`
