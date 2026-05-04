#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constantes y configuración global de SonicVault."""

import customtkinter as ctk

ctk.set_appearance_mode("Dark")

SUPPORTED_EXTENSIONS = (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".mp4")

DEFAULT_CONFIG = {
    "last_folder": "",
    "theme": "Dark",
    "volume": 0.7,
    "window_size": "1000x700"
}

# Paleta de colores

COLORS = {
    "bg_primary":    "#0f0718",
    "bg_secondary":  "#1a1025",
    "bg_tertiary":   "#2e1a47",
    "accent":        "#6d28d9",
    "accent_hover":  "#8b5cf6",
    "accent_bright": "#c4b5fd",
    "text_primary":  "#f5f3ff",
    "text_secondary": "#a78bfa",
    "border":        "#4c1d95",
    "danger":        "#c319b2",
}