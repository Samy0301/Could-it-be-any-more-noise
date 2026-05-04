#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constantes y configuración global de SonicVault."""

import customtkinter as ctk

# Apariencia
ctk.set_appearance_mode("Dark")

# Extensiones soportadas
SUPPORTED_EXTENSIONS = (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".mp4")

# Configuración por defecto
DEFAULT_CONFIG = {
    "last_folder": "",
    "theme": "Dark",
    "volume": 0.7,
    "window_size": "1000x700"
}

# ============================================================================
# PALETA MORADA / PURPURA
# ============================================================================
COLORS = {
    "bg_primary":   "#0a0118",   # Fondo ventana principal (casi negro púrpura)
    "bg_secondary": "#160429",   # Frames / paneles
    "bg_tertiary":  "#240046",   # Inputs, controles, barras
    "accent":       "#7b2cbf",   # Botones, acentos principales
    "accent_hover": "#9d4edd",   # Hover botones
    "accent_bright":"#c77dff",   # Slider knob, highlights
    "text_primary": "#e0aaff",   # Texto principal (lavanda claro)
    "text_secondary":"#9d4edd",  # Texto secundario / placeholders
    "border":       "#3c096c",   # Bordes sutiles
    "danger":       "#ff006e",   # Errores / stop
}