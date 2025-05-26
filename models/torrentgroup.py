from pydantic import BaseModel, Field, ConfigDict
from .torrent import Torrent

class TorrentGroup(BaseModel):
    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    id: int = Field(alias = 'groupId')
    name: str = Field(alias = 'groupName')
    year: int = Field(alias = 'groupYear')
    torrent: list[Torrent]