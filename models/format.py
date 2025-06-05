from dataclasses import dataclass

@dataclass
class Format:
    name: str
    encoding: str
    name_for_files: str | None

    def __eq__(self, value: object) -> bool:
        if isinstance(value, Format):
            return value.name == self.name and value.encoding == self.encoding
        else:
            raise NotImplementedError

    def __hash__(self) -> int:
        return (hash(self.name) ^ hash(self.encoding))

Flac = Format("FLAC", "Lossless", 'FLAC')
MP3_V0 = Format("MP3", "V0 (VBR)", "MP3 V0")
MP3_320 = Format("MP3", "320", 'MP3 320')

perfect_three = set([Flac, MP3_320, MP3_320])