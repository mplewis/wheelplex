from concurrent import futures
from typing import List
from plexapi.server import PlexServer  # type: ignore
from plexapi.video import Movie  # type: ignore

from lib.models import SessionData, ServerMeta


METADATA_WORKER_COUNT = 100


def connect(sess: SessionData) -> PlexServer:
    if not sess.current_server:
        raise ValueError("Server not selected")
    return PlexServer(url_for(sess.current_server), sess.auth_token)


def url_for(server: ServerMeta) -> str:
    return f"{server.scheme}://{server.host}:{server.port}"


def items_for_section(sess: SessionData) -> List[dict]:
    conn = connect(sess)
    items = conn.library.section(sess.current_section).all()

    with futures.ThreadPoolExecutor(max_workers=METADATA_WORKER_COUNT) as executor:
        f: List[futures.Future] = []
        for i in items:
            f.append(executor.submit(meta_for_movie, i))
        results = futures.wait(f)
    return [r.result() for r in results.done]


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
