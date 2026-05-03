#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SonicVault - Reproductor Musical Visual e Intuitivo
====================================================
Módulos:
    utils.py    → Rutas y generador de carátulas
    config.py   → Configuración persistente y favoritos
    metadata.py → Extracción de metadatos de audio
    player.py   → Motor de reproducción en streaming
    ui.py       → Interfaz gráfica con CustomTkinter

Dependencias:
    pip install customtkinter mutagen soundfile sounddevice numpy pillow

Ejecutar:
    python main.py
"""
from ui import SonicVaultApp


def main():
    app = SonicVaultApp()
    app.mainloop()


if __name__ == "__main__":
    main()
