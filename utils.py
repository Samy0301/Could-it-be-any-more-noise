#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilidades: rutas, generador de carátulas y helpers."""

import os
import sys
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw

from constants import COLORS


def get_app_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.resolve()


def get_data_dir() -> Path:
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


@contextmanager
def suppress_stderr():
    """Silencia warnings de librerías C (mpg123, etc.)."""
    devnull = -1
    old_stderr = -1
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        os.dup2(devnull, 2)
        yield
    except Exception:
        yield
    finally:
        if old_stderr >= 0:
            try:
                os.dup2(old_stderr, 2)
                os.close(old_stderr)
            except Exception:
                pass
        if devnull >= 0:
            try:
                os.close(devnull)
            except Exception:
                pass


class CoverGenerator:
    """Genera carátulas por defecto con estética púrpura."""

    def __init__(self, size: tuple[int, int] = (300, 300)):
        self.size = size
        self.default = self._create_default()

    def _create_default(self) -> Image.Image:
        img = Image.new("RGB", self.size, color=COLORS["bg_secondary"])
        draw = ImageDraw.Draw(img)
        cx, cy = self.size[0] // 2, self.size[1] // 2
        r = min(cx, cy) - 40

        # Anillos decorativos morados
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=COLORS["bg_tertiary"], width=10)
        draw.ellipse([cx-r+15, cy-r+15, cx+r-15, cy+r-15], outline=COLORS["accent"], width=6)
        draw.ellipse([cx-r//2, cy-r//2, cx+r//2, cy+r//2], outline=COLORS["accent_bright"], width=3)

        # Nota musical centrada
        draw.text((cx, cy), "♪", fill=COLORS["accent_bright"], anchor="mm")
        return img

    def get_image(self, metadata) -> Image.Image:
        if metadata.cover:
            try:
                img = Image.open(BytesIO(metadata.cover))
                img = img.resize(self.size, Image.Resampling.LANCZOS)
                return img
            except Exception:
                pass
        return self.default