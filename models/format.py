from dataclasses import dataclass
from .encoder import Encoder

@dataclass
class Format:
    name: str
    encoding: str
    long_name: str | None
    encoder: Encoder | None

    def __eq__(self, value: object) -> bool:
        if isinstance(value, Format):
            return value.name == self.name and value.encoding == self.encoding
        else:
            raise NotImplementedError

    def __hash__(self) -> int:
        return (hash(self.name) ^ hash(self.encoding))

Flac = Format("FLAC", "Lossless", 'FLAC',
              Encoder(enc = "flac", ext = ".flac", opts = "--best"))
MP3_V0 = Format("MP3", "V0 (VBR)", "MP3 V0",
                Encoder(enc = "lame", ext = ".mp3", opts = "-V 0 --vbr-new --ignore-tag-errors"))
MP3_V2 = Format("MP3", "V2 (VBR)", "MP3 V2",
                Encoder(enc = "lame", ext = ".mp3", opts = "-V 2 --vbr-new --ignore-tag-errors"))
MP3_320 = Format("MP3", "320", 'MP3 320',
                 Encoder(enc = "lame", ext = ".mp3", opts = "-h -b 320 --ignore-tag-errors"))

perfect_three = set([Flac, MP3_320, MP3_320])