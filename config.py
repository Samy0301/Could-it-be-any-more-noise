"""Configuración persistente y gestión de favoritos."""
import json
from pathlib import Path
from utils import get_data_dir


class AppConfig:
    """Maneja config.json y favorites.json de forma centralizada."""

    def __init__(self):
        self._dir = get_data_dir()
        self._config_path = self._dir / "config.json"
        self._favorites_path = self._dir / "favorites.json"

        self.last_folder: str = ""
        self.theme: str = "Dark"
        self.volume: float = 0.7
        self.window_size: str = "1100x750"
        self.show_favorites_only: bool = False

        self.favorites: list[str] = []
        self._load()

    def _load(self):
        # Configuración general
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                for key in ("last_folder", "theme", "volume", "window_size", "show_favorites_only"):
                    if key in data:
                        setattr(self, key, data[key])
            except Exception:
                pass

        # Favoritos
        if self._favorites_path.exists():
            try:
                self.favorites = json.loads(self._favorites_path.read_text(encoding="utf-8"))
            except Exception:
                self.favorites = []

    def save(self):
        """Guarda configuración y favoritos en disco."""
        config_data = {
            "last_folder": self.last_folder,
            "theme": self.theme,
            "volume": self.volume,
            "window_size": self.window_size,
            "show_favorites_only": self.show_favorites_only,
        }
        self._config_path.write_text(
            json.dumps(config_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self._favorites_path.write_text(
            json.dumps(self.favorites, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def is_favorite(self, path: str) -> bool:
        return path in self.favorites

    def toggle_favorite(self, path: str) -> bool:
        """Añade o quita de favoritos. Devuelve True si ahora es favorito."""
        if path in self.favorites:
            self.favorites.remove(path)
            return False
        self.favorites.append(path)
        return True
