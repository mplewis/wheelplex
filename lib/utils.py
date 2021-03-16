import random
import string
from starlette.responses import HTMLResponse


def refresh(url=None) -> HTMLResponse:
    upart = ""
    if url:
        upart = f";url={url}"
    return HTMLResponse(f'<meta http-equiv="refresh" content="0{upart}" />')


def random_string(len: int) -> str:
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    return "".join(random.SystemRandom().choice(chars) for _ in range(64))


def new_session_string() -> str:
    return random_string(64)
