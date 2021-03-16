import random
import string
import requests
import xmltodict
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from plexapi.server import PlexServer
from fastapi import FastAPI, Request, Response
from starlette.responses import HTMLResponse
from pprint import pprint


SESSION_EXPIRY = timedelta(hours=24)
PLEX_IDENT_HEADERS = {
    "X-Plex-Platform": "MacOS",
    "X-Plex-Platform-Version": "10.15.7",
    "X-Plex-Provides": "controller",
    "X-Plex-Client-Identifier": "wheelplex",
    "X-Plex-Product": "Wheelplex (matt@mplewis.com)",
    "X-Plex-Version": "0.0.1",
    "X-Plex-Device": "MacBookPro15,2",
    "X-Plex-Device-Name": "Matt's MacBook",
}


app = FastAPI()


AuthToken = str


@dataclass
class Pairing:
    pin: str
    id: str


@dataclass
class ServerMeta:
    name: str
    scheme: str
    host: str
    port: str


@dataclass
class SessionData:
    expires_at: datetime
    pairing: Optional[Pairing] = None
    auth_token: Optional[AuthToken] = None
    servers: Optional[List[ServerMeta]] = None
    current_server: Optional[ServerMeta] = None


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
    if not sess.auth_token:
        return pair(sess)

    pprint(sess.auth_token)

    if not sess.servers:
        sess.servers = list_servers(sess.auth_token)

    if not sess.current_server:
        links = [
            f'<a href="/select_server/{s.name}">{s.name}</a>' for s in sess.servers
        ]
        return HTMLResponse(f"<pre><code>{links}</code></pre>")

    return HTMLResponse("<h1>OK</h1>")


@app.get("/select_server/{name}")
def select_server(request: Request, name: str):
    sess = get_session(request)
    if not sess:
        return refresh()
    if not sess.servers:
        sess.servers = list_servers(sess.auth_token)
    for server in sess.servers:
        if name == server.name:
            sess.current_server = server
            return refresh()
    return Response(status_code=404)


def plex_req(method: str, path: str, *, token=None, xml=False) -> dict:
    ext = "json"
    if xml:
        ext = "xml"
    headers = PLEX_IDENT_HEADERS.copy()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.request(method, f"https://plex.tv/{path}.{ext}", headers=headers)
    resp.raise_for_status()
    if xml:
        return xmltodict.parse(resp.text)
    return resp.json()


def start_pairing() -> Pairing:
    data = plex_req("post", "pins")
    return Pairing(pin=data["pin"]["code"], id=data["pin"]["id"])


def finish_pairing(p: Pairing) -> Optional[AuthToken]:
    data = plex_req("get", f"pins/{p.id}")
    return data["pin"]["auth_token"]


def list_servers(t: AuthToken) -> List[ServerMeta]:
    data = plex_req("get", "pms/servers", token=t, xml=True)
    servers = []
    for raw in data["MediaContainer"]["Server"]:
        servers.append(
            ServerMeta(
                name=raw["@name"],
                scheme=raw["@scheme"],
                host=raw["@host"],
                port=raw["@port"],
            )
        )
    return servers


def connect(to: ServerMeta, token: str) -> PlexServer:
    return PlexServer(f"{to.scheme}://{to.host}:{to.port}", token)


def pair(sess: SessionData):
    if not sess.pairing:
        sess.pairing = start_pairing()

    token = finish_pairing(sess.pairing)
    if not token:
        return HTMLResponse(
            f"""
            <p>
                Please visit <a href="https://www.plex.tv/link/">plex.tv/link</a> to pair.
                Use the following token: <code>{sess.pairing.pin}</code>
            </p>
            <p>
                Refresh this page when you're done.
            </p>
            """
        )

    sess.auth_token = token
    return refresh()
