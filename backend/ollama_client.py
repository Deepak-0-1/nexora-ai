import json
import threading
import requests
from backend.config import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_EMBED_MODEL,
    OLLAMA_NUM_CTX, OLLAMA_TEMPERATURE
)

class OllamaError(RuntimeError):
    pass

# Serialize inference: CPU-only machines should not run chat and background jobs concurrently.
INFERENCE_LOCK = threading.Lock()

def check_ollama():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise OllamaError(f"Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}") from e

def stream_chat(messages, temperature=None):
    payload = {
        "model": OLLAMA_MODEL, "messages": messages, "stream": True,
        "keep_alive": -1,
        "options": {
            "temperature": OLLAMA_TEMPERATURE if temperature is None else temperature,
            "num_ctx": OLLAMA_NUM_CTX
        }
    }
    try:
        with INFERENCE_LOCK:
            with requests.post(
                f"{OLLAMA_BASE_URL}/api/chat", json=payload,
                stream=True, timeout=(10, 900)
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("error"):
                        raise OllamaError(data["error"])
                    token = data.get("message", {}).get("content")
                    if token:
                        yield token
    except requests.RequestException as e:
        raise OllamaError(f"Ollama chat request failed: {e}") from e

def chat_once(messages, temperature=0.1, num_predict=700, json_mode=False):
    payload = {
        "model": OLLAMA_MODEL, "messages": messages, "stream": False,
        "keep_alive": -1,
        "options": {"temperature": temperature, "num_predict": num_predict, "num_ctx": OLLAMA_NUM_CTX}
    }
    if json_mode:
        payload["format"] = "json"
    try:
        with INFERENCE_LOCK:
            r = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=(10, 600))
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "")
    except requests.RequestException as e:
        raise OllamaError(f"Ollama request failed: {e}") from e

def embed_text(text):
    try:
        with INFERENCE_LOCK:
            r = requests.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={"model": OLLAMA_EMBED_MODEL, "input": text, "keep_alive": -1},
                timeout=(5, 90)
            )
            r.raise_for_status()
            vectors = r.json().get("embeddings", [])
            return vectors[0] if vectors else None
    except requests.RequestException:
        return None
