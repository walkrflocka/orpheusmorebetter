from pydantic import BaseModel
from . import Torrent

class TorrentGroup(BaseModel):
    groupId: int
    groupName: str
    groupYear: int
    torrent: list[Torrent]