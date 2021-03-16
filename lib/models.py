from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


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
