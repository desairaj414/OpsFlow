# MUST be the very first thing that runs — before any langchain/tiktoken import,
# and before other backend modules import this file.
import os
os.environ["TIKTOKEN_CACHE_DIR"] = "./token"

# Corporate proxy MITM certs break tiktoken's internal downloader (uses `requests`) too — bypass globally.
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

from dotenv import load_dotenv

load_dotenv()

# --- Enterprise GenAI endpoint (generic, OpenAI-compatible) ---
BASE_URL: str = os.getenv("BASE_URL", "https://genailab.tcs.in/v1")
API_KEY: str = os.getenv("API_KEY", "")

# Comma-separated model ids from the event's Participant Handbook.
# Populate this once the handbook is issued — smoke_test.py iterates over ALL of them.
MODELS: list[str] = [m.strip() for m in os.getenv("MODELS", "").split(",") if m.strip()]

# Default chat/embedding models used by the running app (pick from MODELS at event time).
DEFAULT_CHAT_MODEL: str = os.getenv("DEFAULT_CHAT_MODEL", MODELS[0] if MODELS else "")
DEFAULT_EMBED_MODEL: str = os.getenv("DEFAULT_EMBED_MODEL", "")

# --- CORS ---
FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

# --- Mock JWT auth ---
JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-change-me")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
