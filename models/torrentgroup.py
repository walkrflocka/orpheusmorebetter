from pydantic import BaseModel, Field
from .torrent import Torrent

class TorrentGroup(BaseModel):
    id: int = Field(alias = 'groupId')
    name: str = Field(alias = 'groupName')
    year: int = Field(alias = 'groupYear')
    torrent: list[Torrent]