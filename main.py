from datetime import datetime, timedelta
from typing import Optional, Dict, List
from plexapi.server import PlexServer
from fastapi import FastAPI, Request, Response
from starlette.responses import HTMLResponse
from pprint import pprint

from lib.models import SessionData, ServerMeta, AuthToken
from lib.utils import refresh, new_session_string
from lib.pair import pair
from lib.plex_client import plex_req


SESSION_EXPIRY = timedelta(hours=24)


app = FastAPI()


sessions: Dict[str, SessionData] = {}


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
    sess.auth_token = "mthF95mydni-no6G5M4o"
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
            return refresh("/")
    return Response(status_code=404)


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
