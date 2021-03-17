import requests
import xmltodict  # type: ignore
from lib.models import ServerMeta, AuthToken
from typing import List


PLEX_IDENT_HEADERS = {
    "X-Plex-Platform": "Linux",
    "X-Plex-Platform-Version": "0.0.1",
    "X-Plex-Provides": "controller",
    "X-Plex-Client-Identifier": "wheelplex",
    "X-Plex-Product": "Wheelplex Web",
    "X-Plex-Version": "0.0.1",
    "X-Plex-Device": "Linux",
    "X-Plex-Device-Name": "Wheelplex",
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
    servers_to_parse = data["MediaContainer"]["Server"]
    # Plex returns either one server alone or a list of servers. Coerce to list.
    if not isinstance(servers_to_parse, list):
        servers_to_parse = [servers_to_parse]
    servers = []
    for raw in servers_to_parse:
        servers.append(
            ServerMeta(
                name=raw["@name"],
                scheme=raw["@scheme"],
                host=raw["@host"],
                port=raw["@port"],
            )
        )
    return servers
