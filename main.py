import requests
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import HTMLResponse, RedirectResponse

from lib.utils import refresh, new_session_string
from lib.pair import pair
from lib.session import get_session
from lib.plex_discovery import list_servers
from lib.plex_media import connect, url_for, items_for_section


app = FastAPI()


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

    if not sess.servers:
        sess.servers = list_servers(sess.auth_token)

    if not sess.current_server:
        links = [
            f'<a href="/select_server/{s.name}">{s.name}</a>' for s in sess.servers
        ]
        return HTMLResponse(f"Select a server: <pre><code>{links}</code></pre>")

    if not sess.current_section:
        conn = connect(sess)
        links = [
            f'<a href="/select_section/{s.title}">{s.title}</a>'
            for s in conn.library.sections()
        ]
        return HTMLResponse(f"Select a library: <pre><code>{links}</code></pre>")

    return RedirectResponse("wheel.html")


@app.get("/select_server/{name}")
def select_server(request: Request, name: str):
    sess = get_session(request)
    if not sess:
        return refresh()
    if not sess.auth_token:
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


@app.get("/plex_asset/{path:path}")
def proxy_asset(request: Request, path: str):
    sess = get_session(request)
    if not sess:
        return Response(status_code=400)
    if not sess.auth_token:
        return Response(status_code=400)
    if not sess.current_server:
        return Response(status_code=400)
    uri = f"{url_for(sess.current_server)}/{path}"
    resp = requests.get(uri, params={"X-Plex-Token": sess.auth_token}, stream=True)
    resp.raise_for_status()
    return StreamingResponse(resp.raw, media_type=resp.headers["Content-Type"])


app.mount("/", StaticFiles(directory="static"), name="static")
