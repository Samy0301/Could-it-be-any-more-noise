#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constantes y configuración global de SonicVault."""

import customtkinter as ctk

# Apariencia
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Extensiones soportadas
SUPPORTED_EXTENSIONS = (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".mp4")

# Configuración por defecto
DEFAULT_CONFIG = {
    "last_folder": "",
    "theme": "Dark",
    "volume": 0.7,
    "window_size": "1000x700"
}