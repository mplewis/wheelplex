import requests
import xmltodict  # type: ignore
from lib.models import ServerMeta, AuthToken
from typing import List


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