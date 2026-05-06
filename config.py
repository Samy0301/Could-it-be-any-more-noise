#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuración persistente en JSON."""

import json
from pathlib import Path

from utils import get_data_dir
from constants import DEFAULT_CONFIG


class AppConfig:
    """Gestiona la configuración y favoritos guardados en disco."""

    CONFIG_FILE = get_data_dir() / "config.json"
    FAVORITES_FILE = get_data_dir() / "favorites.json"

    def __init__(self):
        self.config = self._load(self.CONFIG_FILE, DEFAULT_CONFIG)
        self.favorites: list[str] = self._load(self.FAVORITES_FILE, [])

    @staticmethod
    def _load(path: Path, default):
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def save_config(self):
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def save_favorites(self):
        with open(self.FAVORITES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.favorites, f, indent=2, ensure_ascii=False)

    # --- Favoritos ---
    def is_favorite(self, path: str) -> bool:
        return path in self.favorites

    def add_favorite(self, path: str):
        if path not in self.favorites:
            self.favorites.append(path)
            self.save_favorites()

    def remove_favorite(self, path: str):
        if path in self.favorites:
            self.favorites.remove(path)
            self.save_favorites()

    def toggle_favorite(self, path: str) -> bool:
        """Devuelve True si quedó como favorito, False si se quitó."""
        if path in self.favorites:
            self.remove_favorite(path)
            return False
        self.add_favorite(path)
        return True