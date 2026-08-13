# MUST be the very first thing that runs — before any langchain/tiktoken import,
# and before other backend modules import this file.
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "./token"

from dotenv import load_dotenv

load_dotenv()

# --- Corporate-proxy SSL bypass — TCS-network-only, gated ---
# The TCS network's MITM proxy breaks tiktoken's internal downloader (uses `requests`) and every
# outbound HTTPS call with a self-signed cert. This is NOT a general-purpose workaround — it must
# only apply when actually running against the TCS network (e.g. locally during the original
# hackathon build), never on the public deploy, where there's no corporate proxy and disabling
# verification globally would be an unforced security regression. Gated behind TCS_NETWORK
# (default off) rather than applied unconditionally at import time as it was originally.
# Per-provider SSL bypass for the `tcs` provider's own outbound calls is handled independently,
# per-client, in api_client.py (mirrors EduCare's providers.py `needs_ssl_bypass` gating) — this
# flag only controls the *global* monkeypatches below, which nothing but the TCS network needs.
TCS_NETWORK: bool = os.getenv("TCS_NETWORK", "false").lower() == "true"

if TCS_NETWORK:
    import ssl
    import requests
    import urllib3

    ssl._create_default_https_context = ssl._create_unverified_context
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _orig_request = requests.Session.request

    def _unverified_request(self, *args, **kwargs):
        kwargs["verify"] = False
        return _orig_request(self, *args, **kwargs)

    requests.Session.request = _unverified_request

# --- Enterprise GenAI endpoint (generic, OpenAI-compatible) — legacy/gated `tcs` provider ---
BASE_URL: str = os.getenv("BASE_URL", "https://genailab.tcs.in/v1")
API_KEY: str = os.getenv("API_KEY", "")

# --- Public multi-provider keys (see providers.py) ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

# Comma-separated model ids from the event's Participant Handbook.
# Populate this once the handbook is issued — smoke_test.py iterates over ALL of them.
MODELS: list[str] = [m.strip() for m in os.getenv("MODELS", "").split(",") if m.strip()]

# Default chat/embedding models used by the running app (pick from MODELS at event time).
DEFAULT_CHAT_MODEL: str = os.getenv("DEFAULT_CHAT_MODEL", MODELS[0] if MODELS else "")
DEFAULT_EMBED_MODEL: str = os.getenv("DEFAULT_EMBED_MODEL", "")

# --- Offline fallback for demo resilience (models-routing.md: "Must still run if the gateway dies
# mid-demo", PRD §3.2) — a local Ollama SLM, only ever invoked when the TCS gateway call itself
# fails. Ollama's OpenAI-compatible server (`ollama serve`, always running per env-network.md).
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_FALLBACK_CHAT_MODEL: str = os.getenv("OLLAMA_FALLBACK_CHAT_MODEL", "llama-3.2-3b-it")
OLLAMA_FALLBACK_EMBED_MODEL: str = os.getenv("OLLAMA_FALLBACK_EMBED_MODEL", "gte-large")

# --- CORS ---
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

# --- Mock JWT auth ---
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-change-me")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
