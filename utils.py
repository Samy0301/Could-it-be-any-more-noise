"""Utilidades compartidas: rutas y generación de carátulas."""
import sys
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw


def get_app_dir() -> Path:
    """Ruta base de la aplicación (compatible con PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.resolve()


def get_data_dir() -> Path:
    """Carpeta data/ dentro de la app."""
    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class CoverGenerator:
    """Genera carátulas por defecto o extrae la incrustada en el audio."""

    def __init__(self, size: tuple[int, int] = (280, 280)):
        self.size = size
        self._default = self._create_default()

    def _create_default(self) -> Image.Image:
        w, h = self.size
        img = Image.new("RGB", (w, h), color="#0f0f1a")
        draw = ImageDraw.Draw(img)
        cx, cy = w // 2, h // 2
        r = min(cx, cy) - 40
        # Círculos decorativos
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline="#1e1e3f", width=6)
        draw.ellipse([cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2], outline="#2a2a5c", width=3)
        # Nota musical
        draw.text((cx, cy), "♪", fill="#e94560", anchor="mm", font_size=72)
        return img

    def get_image(self, cover_data: bytes | None) -> Image.Image:
        """Devuelve PIL.Image desde bytes o la imagen por defecto."""
        if cover_data:
            try:
                img = Image.open(BytesIO(cover_data))
                return img.convert("RGB").resize(self.size, Image.Resampling.LANCZOS)
            except Exception:
                pass
        return self._default.copy()
