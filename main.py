import random
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict

from fastapi import FastAPI, Request
from fastapi.security import APIKeyCookie
from starlette.responses import HTMLResponse


SESSION_EXPIRY = timedelta(hours=24)


app = FastAPI()

cookie_sec = APIKeyCookie(name="session")


@dataclass
class PairingPin:
    pin: str
    id: str


@dataclass
class SessionData:
    expires_at: datetime
    pairing_pin: Optional[PairingPin] = None


sessions: Dict[str, SessionData] = {}


def new_session() -> SessionData:
    return SessionData(expires_at=datetime.now() + SESSION_EXPIRY)


def refresh() -> HTMLResponse:
    return HTMLResponse('<meta http-equiv="refresh" content="0" />')


def get_session(request: Request) -> Optional[SessionData]:
    token = request.cookies.get("session")
    if not token:
        return None
    s = sessions.get(token)
    if not s or s.expires_at <= datetime.now():
        s = new_session()
        sessions[token] = s
    return s


def random_string(len: int) -> str:
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(random.SystemRandom().choice(chars) for _ in range(64))


def new_session_string() -> str:
    return random_string(64)


@app.middleware("http")
async def set_cookie_if_unset(request: Request, call_next):
    existing_token = request.cookies.get("session")
    response = await call_next(request)
    if not existing_token:
        response.set_cookie("session", new_session_string())
    return response


@app.get("/")
def login_page(request: Request):
    sess = get_session(request)
    if not sess:
        return refresh()

    return HTMLResponse(
        """
        <h1>Hello world!</h1>
        <p>We have set your session cookie.</p>
        """
    )
