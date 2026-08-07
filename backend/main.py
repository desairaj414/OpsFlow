# MUST be first — before any langchain/tiktoken import.
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

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

import config
from api_client import get_llm

app = FastAPI(title="Hackathon Boilerplate API")

# --- CORS: allow the Next.js/Vite frontend origin ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------------- Mock JWT auth ----------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=config.JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Mock only — replace with real user store before production use.
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    token = create_access_token(subject=form_data.username)
    return TokenResponse(access_token=token)


@app.get("/auth/me")
def read_me(current_user: str = Depends(get_current_user)):
    return {"username": current_user}


# ---------------- Health ----------------
@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------- Example chat endpoint ----------------
class ChatRequest(BaseModel):
    message: str
    model: str | None = None


@app.post("/chat")
def chat(req: ChatRequest, current_user: str = Depends(get_current_user)):
    llm = get_llm(model=req.model)
    response = llm.invoke(req.message)
    return {"reply": response.content}
