import requests
import concurrent
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from plexapi.server import PlexServer
from plexapi.video import Movie
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from starlette.responses import HTMLResponse, RedirectResponse
from pprint import pprint

from lib.models import SessionData, ServerMeta, AuthToken
from lib.utils import refresh, new_session_string
from lib.pair import pair
from lib.plex_client import plex_req


SESSION_EXPIRY = timedelta(hours=24)
METADATA_WORKER_COUNT = 100


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
def home(request: Request):
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

    if not sess.current_section:
        conn = connect(sess)
        links = [
            f'<a href="/select_section/{s.title}">{s.title}</a>'
            for s in conn.library.sections()
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
            return RedirectResponse("/")
    return Response(status_code=404)


@app.get("/select_section/{name}")
def select_section(request: Request, name: str):
    sess = get_session(request)
    if not sess:
        return refresh()
    sess.current_section = name
    return RedirectResponse("/")


@app.get("/list")
def list_items(request: Request):
    sess = get_session(request)
    if not sess:
        return Response(status_code=400)
    if not sess.current_server:
        return Response(status_code=400)
    if not sess.current_section:
        return Response(status_code=400)

    return items_for_section(sess)


def meta_for_movie(i: Movie) -> dict:
    return {
        "title": i.title,
        "audience_rating": i.audienceRating,
        "critic_rating": i.rating,
        "summary": i.summary,
        "genres": [g.tag for g in i.genres],
        "thumbnail_url": f"/plex_asset{i.thumb}",
        "viewed_at": i.viewedAt,
    }


def items_for_section(sess: SessionData) -> List[dict]:
    conn = connect(sess)
    items = conn.library.section(sess.current_section).all()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=METADATA_WORKER_COUNT
    ) as executor:
        futures = []
        for i in items:
            futures.append(executor.submit(meta_for_movie, i))
        results = concurrent.futures.wait(futures)
    return [r.result() for r in results.done]


@app.get("/plex_asset/{path:path}")
def proxy_asset(request: Request, path: str):
    sess = get_session(request)
    if not sess:
        return Response(status_code=400)
    if not sess.auth_token:
        return Response(status_code=400)
    uri = f"{url_for(sess.current_server)}/{path}"
    resp = requests.get(uri, params={"X-Plex-Token": sess.auth_token}, stream=True)
    resp.raise_for_status()
    return StreamingResponse(resp.raw, media_type=resp.headers["Content-Type"])


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


def url_for(server: ServerMeta) -> str:
    return f"{server.scheme}://{server.host}:{server.port}"


def connect(sess: SessionData) -> PlexServer:
    return PlexServer(url_for(sess.current_server), sess.auth_token)
