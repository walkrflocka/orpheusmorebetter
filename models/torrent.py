from pydantic import BaseModel

class Torrent(BaseModel):
    id: int
    groupId: int
    media: str
    format: str
    seeders: int
    remastered: bool
    description: str
    remasterYear: str
    remasterTitle: str
    remasterRecordLabel: str
    remasterCatalogueNumber: str