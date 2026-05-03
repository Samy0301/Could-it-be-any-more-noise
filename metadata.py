"""Extracción de metadatos de archivos de audio soportados."""
from pathlib import Path

SUPPORTED_EXTS = (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".mp4")


class AudioMetadata:
    """Representa los metadatos de una pista de audio."""

    def __init__(self, filepath: str):
        self.path: str = filepath
        self.title: str = Path(filepath).stem
        self.artist: str = "Artista desconocido"
        self.album: str = "Álbum desconocido"
        self.duration: float = 0.0
        self.cover: bytes | None = None
        self._extract()

    def _extract(self):
        ext = Path(self.path).suffix.lower()
        try:
            if ext == ".mp3":
                self._from_mp3()
            elif ext == ".flac":
                self._from_flac()
            elif ext == ".wav":
                self._from_wav()
            elif ext == ".ogg":
                self._from_ogg()
            elif ext in (".m4a", ".mp4"):
                self._from_m4a()
        except Exception:
            pass

    def _from_mp3(self):
        from mutagen.mp3 import MP3
        audio = MP3(self.path)
        self.duration = audio.info.length
        if audio.tags:
            self.title = self._tag(audio.tags, "TIT2", self.title)
            self.artist = self._tag(audio.tags, "TPE1", self.artist)
            self.album = self._tag(audio.tags, "TALB", self.album)

    def _from_flac(self):
        from mutagen.flac import FLAC
        audio = FLAC(self.path)
        self.duration = audio.info.length
        if audio.tags:
            self.title = audio.get("title", [self.title])[0]
            self.artist = audio.get("artist", [self.artist])[0]
            self.album = audio.get("album", [self.album])[0]
        if audio.pictures:
            self.cover = audio.pictures[0].data

    def _from_wav(self):
        from mutagen.wave import WAVE
        audio = WAVE(self.path)
        self.duration = audio.info.length

    def _from_ogg(self):
        from mutagen.oggvorbis import OggVorbis
        audio = OggVorbis(self.path)
        self.duration = audio.info.length
        if audio.tags:
            self.title = audio.get("title", [self.title])[0]
            self.artist = audio.get("artist", [self.artist])[0]
            self.album = audio.get("album", [self.album])[0]

    def _from_m4a(self):
        from mutagen.mp4 import MP4
        audio = MP4(self.path)
        self.duration = audio.info.length
        if "\xa9nam" in audio:
            self.title = str(audio["\xa9nam"][0])
        if "\xa9ART" in audio:
            self.artist = str(audio["\xa9ART"][0])
        if "\xa9alb" in audio:
            self.album = str(audio["\xa9alb"][0])

    @staticmethod
    def _tag(tags, key: str, default: str) -> str:
        val = tags.get(key)
        return str(val[0]) if val else default

    @property
    def formatted_duration(self) -> str:
        m, s = divmod(int(self.duration), 60)
        return f"{m:02d}:{s:02d}"

    def __repr__(self) -> str:
        return f"AudioMetadata({self.title!r} — {self.artist!r})"
