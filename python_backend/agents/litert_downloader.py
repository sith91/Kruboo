"""
LiteRT-LM Model Downloader
Downloads Gemma 4 E2B-IT model from HuggingFace for local inference.
"""
import os
import sys
import urllib.request
import json

MODEL_DIR = os.path.expanduser("~/.cache/litert-lm")
DEFAULT_MODEL_NAME = "gemma-4-E2B-it"

# HuggingFace repo for the model
HF_REPO = "litert-community/gemma-4-E2B-it-litert-lm"
HF_API_URL = f"https://huggingface.co/api/models/{HF_REPO}"

def get_model_path():
    """Return the path where the model is/should be stored."""
    return os.path.join(MODEL_DIR, f"{DEFAULT_MODEL_NAME}.litertlm")

def model_exists():
    """Check if the model is already downloaded."""
    path = get_model_path()
    return os.path.exists(path) and os.path.getsize(path) > 100_000_000  # >100MB sanity check

def _get_download_url():
    """Resolve the actual download URL from HuggingFace API."""
    # Preferred filenames in priority order (GPU for Metal acceleration on macOS)
    preferred = ["gemma-4-E2B-it-gpu.litertlm", "gemma-4-E2B-it.litertlm"]
    try:
        req = urllib.request.Request(HF_API_URL, headers={"User-Agent": "Kruuboo/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            siblings = data.get("siblings", [])
            filenames = [f.get("rfilename", "") for f in siblings]
            # Try preferred files first
            for pref in preferred:
                if pref in filenames:
                    return f"https://huggingface.co/{HF_REPO}/resolve/main/{pref}"
            # Fallback to any .litertlm
            for fname in filenames:
                if fname.endswith(".litertlm"):
                    return f"https://huggingface.co/{HF_REPO}/resolve/main/{fname}"
    except Exception as e:
        print(f"[LiteRT Downloader] Failed to query HF API: {e}")
    
    # Fallback — try the GPU filename directly
    return f"https://huggingface.co/{HF_REPO}/resolve/main/gemma-4-E2B-it-gpu.litertlm"

def download_model(progress_callback=None):
    """
    Download the Gemma 4 E2B model.
    progress_callback(downloaded_bytes, total_bytes) is called periodically.
    Returns the model path on success, None on failure.
    """
    if model_exists():
        print(f"[LiteRT Downloader] Model already exists at {get_model_path()}")
        return get_model_path()
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    url = _get_download_url()
    dest = get_model_path()
    temp_dest = dest + ".downloading"
    
    print(f"[LiteRT Downloader] Downloading from: {url}")
    print(f"[LiteRT Downloader] Saving to: {dest}")
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Kruuboo/1.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 256  # 256KB chunks
            
            with open(temp_dest, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if progress_callback:
                        progress_callback(downloaded, total)
                    elif total > 0:
                        pct = (downloaded / total) * 100
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        print(f"\r[LiteRT Downloader] {mb_done:.1f}/{mb_total:.1f} MB ({pct:.1f}%)", end="", flush=True)
            
            print()  # newline after progress
        
        # Rename temp file to final
        os.rename(temp_dest, dest)
        print(f"[LiteRT Downloader] Download complete: {dest}")
        return dest
        
    except Exception as e:
        print(f"\n[LiteRT Downloader] Download failed: {e}")
        if os.path.exists(temp_dest):
            os.remove(temp_dest)
        return None

if __name__ == "__main__":
    if model_exists():
        print(f"Model already downloaded: {get_model_path()}")
    else:
        print("Starting Gemma 4 E2B-IT download...")
        result = download_model()
        sys.exit(0 if result else 1)
