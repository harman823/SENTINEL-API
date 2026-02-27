import logging
import socket

logger = logging.getLogger(__name__)

# ── Fast health check ──
_ollama_available: bool | None = None
OLLAMA_HOST = "localhost"
OLLAMA_PORT = 11434


def is_ollama_available() -> bool:
    """
    Ultra-fast TCP check if Ollama is running (no HTTP overhead).
    Result is cached so it only checks once per process.
    """
    global _ollama_available
    if _ollama_available is not None:
        return _ollama_available
    try:
        sock = socket.create_connection((OLLAMA_HOST, OLLAMA_PORT), timeout=1.0)
        sock.close()
        _ollama_available = True
    except (socket.timeout, ConnectionRefusedError, OSError):
        _ollama_available = False
    if not _ollama_available:
        logger.warning("Ollama not reachable — AI features use instant heuristic fallbacks.")
    return _ollama_available


# ── Lazy singleton instances ──
_llm_json_cache: dict = {}
_llm_text_cache: dict = {}


def get_llm(model_name: str = "llama3.2", temperature: float = 0.0):
    """
    Returns a cached ChatOllama (JSON mode) or None if Ollama is unavailable.
    Import is lazy to avoid slow module load at startup.
    """
    if not is_ollama_available():
        return None
    key = (model_name, temperature)
    if key not in _llm_json_cache:
        from langchain_ollama import ChatOllama
        _llm_json_cache[key] = ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}",
            format="json",
            num_predict=512,
            num_ctx=2048,
        )
    return _llm_json_cache[key]


def get_llm_text(model_name: str = "llama3.2", temperature: float = 0.4):
    """
    Returns a cached ChatOllama (text mode) or None if Ollama is unavailable.
    Import is lazy to avoid slow module load at startup.
    """
    if not is_ollama_available():
        return None
    key = (model_name, temperature)
    if key not in _llm_text_cache:
        from langchain_ollama import ChatOllama
        _llm_text_cache[key] = ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=f"http://{OLLAMA_HOST}:{OLLAMA_PORT}",
            num_predict=512,
            num_ctx=2048,
        )
    return _llm_text_cache[key]
