from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Request

from lib.models import SessionData


SESSION_EXPIRY = timedelta(hours=24)


sessions: Dict[str, SessionData] = {}  # in-memory store


def new_session() -> SessionData:
    return SessionData(expires_at=datetime.now() + SESSION_EXPIRY)


def get_session(request: Request) -> Optional[SessionData]:
    token = request.cookies.get("session")
    if not token:
        return None
    s = sessions.get(token)
    if not s or s.expires_at <= datetime.now():
        s = new_session()
        sessions[token] = s
    return s
