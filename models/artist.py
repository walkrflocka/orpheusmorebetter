from pydantic import BaseModel
from . import TorrentGroup

class Artist(BaseModel):
    id: int
    name: str
    torrentgroup: list[TorrentGroup]