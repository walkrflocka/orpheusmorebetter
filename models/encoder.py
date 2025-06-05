from dataclasses import dataclass

@dataclass
class Encoder:
    enc: str
    ext: str
    opts: str


encoders = {
    "320": Encoder(enc = "lame", ext = ".mp3", opts = "-h -b 320 --ignore-tag-errors"),
    "V0": Encoder(enc = "lame", ext = ".mp3", opts = "-V 0 --vbr-new --ignore-tag-errors"),
    "V2": Encoder(enc = "lame", ext = ".mp3", opts = "-V 2 --vbr-new --ignore-tag-errors"),
    "FLAC": Encoder(enc = "flac", ext = ".flac", opts = "--best")
}