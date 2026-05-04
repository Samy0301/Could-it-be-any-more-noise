#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilidades: rutas, generador de carátulas y helpers."""

import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from constants import SUPPORTED_EXTENSIONS

import os
from contextlib import contextmanager


def get_app_dir() -> Path:
    """Devuelve la carpeta donde reside la aplicación (compatible con PyInstaller)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.resolve()


def get_data_dir() -> Path:
    """Crea y devuelve la carpeta de datos persistentes."""
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class CoverGenerator:
    """Genera carátulas por defecto o extrae la incrustada en el archivo."""

    def __init__(self, size: tuple[int, int] = (300, 300)):
        self.size = size
        self.default = self._create_default()

    def _create_default(self) -> Image.Image:
        img = Image.new("RGB", self.size, color="#1a1a2e")
        draw = ImageDraw.Draw(img)
        cx, cy = self.size[0] // 2, self.size[1] // 2
        r = min(cx, cy) - 40
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#16213e", width=8)
        draw.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], outline="#0f3460", width=4)
        draw.text((cx, cy), "♪", fill="#e94560", anchor="mm")
        return img

    def get_image(self, metadata) -> Image.Image:
        """Devuelve la carátula extraída o la imagen por defecto."""
        if metadata.cover:
            try:
                img = Image.open(BytesIO(metadata.cover))
                img = img.resize(self.size, Image.Resampling.LANCZOS)
                return img
            except Exception:
                pass
        return self.default
    

@contextmanager
def suppress_stderr():
    """Redirige stderr a /dev/null para silenciar warnings de librerías C (mpg123, etc.)."""
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)  # fd 2 = stderr
        os.dup2(devnull, 2)
        yield
    except Exception:
        yield
    finally:
        try:
            os.dup2(old_stderr, 2)
            os.close(old_stderr)
            os.close(devnull)
        except Exception:
            pass