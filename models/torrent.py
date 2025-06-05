from pydantic import BaseModel
import re

from .format import Format, perfect_three

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

    @property
    def formatted_media_info(self) -> str:
        media_info: str
        if self.remasterTitle is not None and self.remasterTitle != '':
            media_info = f"{{{self.media} ~ {self.remasterTitle} {self.remasterYear}}}"
        else:
            media_info = f"{{{self.media}}}"

        return media_info

    @property
    def allowed_transcodes(self) -> set[Format]:
        """Some torrent types have transcoding restrictions."""
        preemphasis = re.search(
            r"pre[- ]?emphasi(s(ed)?|zed)", self.remasterTitle, flags=re.IGNORECASE
        )
        if preemphasis:
            return set()
        else:
            return perfect_three