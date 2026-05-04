#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SonicVault 🎵 — Lista izquierda | Reproducción derecha (ancho fijo)
"""

import random
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from config import AppConfig
from constants import SUPPORTED_EXTENSIONS, COLORS
from metadata import AudioMetadata
from player import MusicPlayer
from utils import CoverGenerator


class SonicVaultApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.player = MusicPlayer()
        self.cover_gen = CoverGenerator((280, 280))
        self.songs: list[AudioMetadata] = []
        self.filtered_songs: list[AudioMetadata] = []
        self.current_index = -1
        self.after_id = None
        self._is_seeking = False

        self.title("SonicVault 🎵")
        self.geometry(self.config.config.get("window_size", "1000x700"))
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_primary"])

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        last = self.config.config.get("last_folder", "")
        if last and Path(last).exists():
            self._load_folder(last)

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ===== TOP BAR =====
        self.top_frame = ctk.CTkFrame(
            self, height=60, fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"], border_width=1, corner_radius=12
        )
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 8))
        self.top_frame.grid_propagate(False)
        self.top_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            self.top_frame,
            placeholder_text="🔍  Buscar canción, artista o álbum...",
            font=("Roboto", 14),
            fg_color=COLORS["bg_tertiary"],
            text_color=COLORS["text_primary"],
            placeholder_text_color=COLORS["text_secondary"],
            border_color=COLORS["border"],
            corner_radius=10,
            height=38
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(12, 10), pady=10)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        self.btn_folder = ctk.CTkButton(
            self.top_frame, text="📁  Abrir Carpeta", width=130,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"], font=("Roboto", 13, "bold"),
            corner_radius=10, height=34,
            command=self._select_folder
        )
        self.btn_folder.grid(row=0, column=1, padx=(0, 10), pady=10)

        self.btn_random = ctk.CTkButton(
            self.top_frame, text="🎲  Random", width=110,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"], font=("Roboto", 13),
            border_color=COLORS["accent"], border_width=1,
            corner_radius=10, height=34,
            command=self._play_random
        )
        self.btn_random.grid(row=0, column=2, padx=(0, 12), pady=10)

        # ===== CONTENT =====
        self.content_frame = ctk.CTkFrame(
            self, fg_color="transparent"
        )
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        # Solo la columna 0 (lista) crece. La columna 1 (reproducción) es ancho fijo.
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # -- Left: Song List --
        self.right_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"], border_width=1, corner_radius=16
        )
        self.right_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.right_frame.grid_rowconfigure(0, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.right_frame,
            label_text="  📀  Biblioteca  ",
            label_font=("Roboto", 16, "bold"),
            label_text_color=COLORS["text_primary"],
            label_fg_color=COLORS["bg_tertiary"],
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_color=COLORS["border"], border_width=0
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.list_widgets: list[ctk.CTkFrame] = []

        # -- Right: Now Playing (ancho fijo = 280 portada + 40 márgenes) --
        self.left_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"], border_width=1, corner_radius=16,
            width=350  # <-- ANCHO FIJO exacto para la portada + paddings
        )
        self.left_frame.grid(row=0, column=1, sticky="ns")  # ns = solo vertical, no horizontal
        self.left_frame.grid_propagate(False)  # <-- Mantiene el ancho fijo sin importar el contenido
        self.content_frame.grid_columnconfigure(1, minsize=350)
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(1, weight=0)

        # Portada
        self.cover_label = ctk.CTkLabel(
            self.left_frame, text="", fg_color="transparent"
        )
        self.cover_label.grid(row=0, column=0, padx=35, pady=20, sticky="n")

        # Info
        self.info_frame = ctk.CTkFrame(
            self.left_frame, fg_color=COLORS["bg_tertiary"],
            corner_radius=12
        )
        self.info_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 12))

        self.lbl_title = ctk.CTkLabel(
            self.info_frame, text="Sin reproducción",
            font=("Roboto", 20, "bold"), text_color=COLORS["text_primary"],
            wraplength=280
        )
        self.lbl_title.pack(pady=(14, 4))

        self.lbl_artist = ctk.CTkLabel(
            self.info_frame, text="Selecciona una carpeta",
            font=("Roboto", 14), text_color=COLORS["text_secondary"]
        )
        self.lbl_artist.pack(pady=(0, 2))

        self.lbl_album = ctk.CTkLabel(
            self.info_frame, text="",
            font=("Roboto", 12), text_color=COLORS["accent_bright"]
        )
        self.lbl_album.pack(pady=(0, 12))

        # Controls
        self.controls_frame = ctk.CTkFrame(
            self.left_frame, fg_color="transparent"
        )
        self.controls_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        btn_style = {
            "fg_color": COLORS["accent"],
            "hover_color": COLORS["accent_hover"],
            "text_color": COLORS["text_primary"],
            "corner_radius": 10,
            "font": ("Roboto", 16),
            "height": 36
        }

        self.btn_prev = ctk.CTkButton(
            self.controls_frame, text="⏮", width=50, **btn_style,
            command=self._prev_song
        )
        self.btn_prev.pack(side="left", padx=6)

        self.btn_play = ctk.CTkButton(
            self.controls_frame, text="▶", width=70,
            fg_color=COLORS["accent_bright"], hover_color=COLORS["accent"],
            text_color=COLORS["bg_primary"], font=("Roboto", 18, "bold"),
            corner_radius=12, height=42,
            command=self._toggle_play
        )
        self.btn_play.pack(side="left", padx=8)

        self.btn_next = ctk.CTkButton(
            self.controls_frame, text="⏭", width=50, **btn_style,
            command=self._next_song
        )
        self.btn_next.pack(side="left", padx=6)

        self.lbl_time = ctk.CTkLabel(
            self.controls_frame, text="00:00 / 00:00",
            font=("Roboto", 13), text_color=COLORS["text_secondary"]
        )
        self.lbl_time.pack(side="right", padx=10)

        # Progress slider
        self.progress = ctk.CTkSlider(
            self.left_frame, from_=0, to=1000, state="disabled",
            fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent"],
            button_color=COLORS["accent_bright"], button_hover_color=COLORS["accent_hover"],
            height=16, corner_radius=8
        )
        self.progress.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 6))
        self.progress.bind("<ButtonPress-1>", lambda e: setattr(self, "_is_seeking", True))
        self.progress.bind("<ButtonRelease-1>", self._on_seek)

        # Volume
        self.vol_slider = ctk.CTkSlider(
            self.left_frame, from_=0, to=1,
            fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent_bright"],
            button_color=COLORS["accent"], button_hover_color=COLORS["accent_hover"],
            height=12, corner_radius=6,
            command=self._set_volume
        )
        self.vol_slider.set(self.config.config.get("volume", 0.7))
        self.vol_slider.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.player.set_volume(self.vol_slider.get())

        # Status bar
        self.status = ctk.CTkLabel(
            self, text="✦ Listo",
            font=("Roboto", 12), text_color=COLORS["text_secondary"],
            anchor="w", fg_color="transparent"
        )
        self.status.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 12))

        # Update loop
        self._update_loop()

    # ========================================================================
    # CARPETA Y LISTA
    # ========================================================================
    def _select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self._load_folder(folder)

    def _load_folder(self, folder: str):
        self.config.config["last_folder"] = folder
        self.config.save_config()
        self.status.configure(text=f"✦ Cargando: {folder}")
        self.update_idletasks()

        self.songs.clear()
        path = Path(folder)
        for f in sorted(path.rglob("*")):
            if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.songs.append(AudioMetadata(str(f)))

        self.filtered_songs = self.songs.copy()
        self._render_list()
        self.status.configure(text=f"✦ {len(self.songs)} canciones cargadas")

    def _render_list(self):
        for w in self.list_widgets:
            w.destroy()
        self.list_widgets.clear()

        for idx, meta in enumerate(self.filtered_songs):
            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=COLORS["bg_tertiary"],
                corner_radius=8,
                border_color=COLORS["border"], border_width=1
            )
            row.grid(sticky="ew", pady=3, padx=2)
            row.grid_columnconfigure(0, weight=1)
            row.bind("<Enter>", lambda e, r=row: r.configure(fg_color=COLORS["accent"]))
            row.bind("<Leave>", lambda e, r=row: r.configure(fg_color=COLORS["bg_tertiary"]))
            row.bind("<Button-1>", lambda e, i=idx: self._select_song(i))

            lbl = ctk.CTkLabel(
                row,
                text=f"{meta.title}  —  {meta.artist}  ({meta.format_duration()})",
                anchor="w", font=("Roboto", 12),
                text_color=COLORS["text_primary"]
            )
            lbl.grid(row=0, column=0, sticky="w", padx=12, pady=10)
            lbl.bind("<Button-1>", lambda e, i=idx: self._select_song(i))

            self.list_widgets.append(row)

    def _on_search(self, event=None):
        query = self.search_entry.get().lower()
        if not query:
            self.filtered_songs = self.songs.copy()
        else:
            self.filtered_songs = [
                s for s in self.songs
                if query in s.title.lower()
                or query in s.artist.lower()
                or query in s.album.lower()
            ]
        self._render_list()

    # ========================================================================
    # REPRODUCCIÓN
    # ========================================================================
    def _select_song(self, filtered_idx: int):
        if not self.filtered_songs:
            return
        meta = self.filtered_songs[filtered_idx]
        try:
            self.current_index = self.songs.index(meta)
        except ValueError:
            return
        self._play_current()

    def _play_current(self):
        if self.current_index < 0 or self.current_index >= len(self.songs):
            return
        meta = self.songs[self.current_index]

        try:
            self.player.load(meta.path)
            self.player.play()
        except Exception as e:
            self.status.configure(text=f"✦ Error: {str(e)[:60]}")
            self.after(1000, self._next_song)
            return

        self.lbl_title.configure(text=meta.title)
        self.lbl_artist.configure(text=meta.artist)
        self.lbl_album.configure(text=f"{meta.album}  •  {meta.format_duration()}")

        img = self.cover_gen.get_image(meta)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(280, 280))
        self.cover_label.configure(image=ctk_img, text="")
        self.cover_label.image = ctk_img  # type: ignore[attr-defined]

        self.btn_play.configure(text="⏸")
        self.progress.configure(state="normal")
        self.status.configure(text="✦ Reproduciendo")

    def _toggle_play(self):
        if not self.player.has_file():
            if self.songs:
                self.current_index = 0
                self._play_current()
            return

        if self.player.is_playing():
            self.player.pause()
            self.btn_play.configure(text="▶")
        else:
            self.player.resume()
            self.btn_play.configure(text="⏸")

    def _prev_song(self):
        if not self.songs:
            return
        self.current_index = (self.current_index - 1) % len(self.songs)
        self._play_current()

    def _next_song(self):
        if not self.songs:
            return
        self.current_index = (self.current_index + 1) % len(self.songs)
        self._play_current()

    def _play_random(self):
        if not self.songs:
            return
        self.current_index = random.randint(0, len(self.songs) - 1)
        self._play_current()

    def _set_volume(self, val):
        vol = float(val)
        self.player.set_volume(vol)
        self.config.config["volume"] = vol

    def _on_seek(self, event=None):
        self._is_seeking = False
        if self.current_index >= 0 and self.songs:
            ratio = self.progress.get() / 1000
            seconds = self.songs[self.current_index].duration * ratio
            self.player.seek(seconds)

    def _update_loop(self):
        if self.current_index >= 0 and self.songs and not self._is_seeking:
            pos = self.player.get_pos()
            dur = self.songs[self.current_index].duration

            self.lbl_time.configure(text=f"{self._fmt(pos)} / {self._fmt(dur)}")

            if dur > 0:
                self.progress.set(int((pos / dur) * 1000))

            if self.player.is_finished() and not self.player.is_paused():
                self._next_song()

        self.after_id = self.after(500, self._update_loop)

    @staticmethod
    def _fmt(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    # ========================================================================
    # CIERRE
    # ========================================================================
    def _on_close(self):
        self.config.save_config()
        self.config.save_favorites()
        if self.after_id:
            self.after_cancel(self.after_id)
        self.player.stop()
        self.destroy()


if __name__ == "__main__":
    app = SonicVaultApp()
    app.mainloop()