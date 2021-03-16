from typing import Optional
from starlette.responses import HTMLResponse

from lib.models import SessionData, AuthToken, Pairing
from lib.utils import refresh
from lib.plex_client import plex_req


def start_pairing() -> Pairing:
    data = plex_req("post", "pins")
    return Pairing(pin=data["pin"]["code"], id=data["pin"]["id"])


def finish_pairing(p: Pairing) -> Optional[AuthToken]:
    data = plex_req("get", f"pins/{p.id}")
    return data["pin"]["auth_token"]


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
