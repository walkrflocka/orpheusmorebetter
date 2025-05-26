from pydantic import BaseModel

class Torrent(BaseModel):
    id: int
    groupId: int | None = None
    media: str
    format: str
    seeders: int
    snatched: int
    remastered: bool
    description: str
    remasterYear: int | None = None
    remasterTitle: str
    remasterRecordLabel: str
    remasterCatalogueNumber: str
    fileList: str
    filePath: str
    encoding: str