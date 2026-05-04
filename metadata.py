#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extracción de metadatos y portadas de archivos de audio."""

from pathlib import Path

from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.wave import WAVE
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
from mutagen.id3 import APIC

from constants import SUPPORTED_EXTENSIONS


class AudioMetadata:
    """Representa los metadatos de una pista de audio."""

    def __init__(self, filepath: str):
        self.path = filepath
        self.title = Path(filepath).stem
        self.artist = "Artista desconocido"
        self.album = "Álbum desconocido"
        self.year = ""
        self.genre = ""
        self.duration = 0.0
        self.cover = None
        self._extract()

    def _extract(self):
        ext = Path(self.path).suffix.lower()
        try:
            if ext == ".mp3":
                self._extract_mp3()
            elif ext == ".flac":
                self._extract_flac()
            elif ext == ".wav":
                self._extract_wav()
            elif ext == ".ogg":
                self._extract_ogg()
            elif ext in (".m4a", ".mp4"):
                self._extract_m4a()
        except Exception:
            pass

    def _extract_mp3(self):
        audio = MP3(self.path)
        self.duration = audio.info.length
        if audio.tags:
            self.title = self._tag(audio.tags, "TIT2", self.title)
            self.artist = self._tag(audio.tags, "TPE1", "Artista desconocido")
            self.album = self._tag(audio.tags, "TALB", "Álbum desconocido")
            # --- PORTADA MP3 (ID3/APIC) ---
            for tag in audio.tags.values():
                if isinstance(tag, APIC):
                    self.cover = tag.data
                    break

    def _extract_flac(self):
        audio = FLAC(self.path)
        self.duration = audio.info.length
        self.title = self._tag(audio, "title", self.title)
        self.artist = self._tag(audio, "artist", "Artista desconocido")
        self.album = self._tag(audio, "album", "Álbum desconocido")
        # --- PORTADA FLAC ---
        if audio.pictures:
            self.cover = audio.pictures[0].data

    def _extract_wav(self):
        audio = WAVE(self.path)
        self.duration = audio.info.length

    def _extract_ogg(self):
        audio = OggVorbis(self.path)
        self.duration = audio.info.length
        self.title = self._tag(audio, "title", self.title)
        self.artist = self._tag(audio, "artist", "Artista desconocido")
        self.album = self._tag(audio, "album", "Álbum desconocido")
        # --- PORTADA OGG (METADATA_BLOCK_PICTURE) ---
        if "metadata_block_picture" in audio:
            try:
                import base64
                pic_data = base64.b64decode(audio["metadata_block_picture"][0])
                pic = Picture(pic_data)
                self.cover = pic.data
            except Exception:
                pass

    def _extract_m4a(self):
        audio = MP4(self.path)
        self.duration = audio.info.length
        if "\xa9nam" in audio:
            self.title = str(audio["\xa9nam"][0])
        if "\xa9ART" in audio:
            self.artist = str(audio["\xa9ART"][0])
        if "\xa9alb" in audio:
            self.album = str(audio["\xa9alb"][0])
        # --- PORTADA M4A/MP4 (covr) ---
        if "covr" in audio:
            try:
                self.cover = bytes(audio["covr"][0])
            except Exception:
                pass

    @staticmethod
    def _tag(audio_obj, key: str, default: str) -> str:
        """Extrae un tag de forma segura."""
        if hasattr(audio_obj, "get"):
            values = audio_obj.get(key, [default])
            return str(values[0]) if values else default
        return default

    def format_duration(self) -> str:
        m, s = divmod(int(self.duration), 60)
        return f"{m:02d}:{s:02d}"