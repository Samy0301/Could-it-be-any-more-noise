#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SonicVault 🎵 — Optimizado: sin reconstrucción de lista
"""

import random
from pathlib import Path
from tkinter import filedialog, Menu

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

        self.play_history: list[int] = []
        self.history_index = -1
        self._error_count = 0

        self.play_mode = self.config.config.get("play_mode", "queue")
        self.up_next: list[int] = []

        self._song_path_to_idx: dict[str, int] = {}
        self._search_after_id = None
        self.showing_favorites = False

        self.title("SonicVault 🎵")
        self.geometry(self.config.config.get("window_size", "1000x700"))
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg_primary"])

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        last = self.config.config.get("last_folder", "")
        if last and Path(last).exists():
            self._load_folder(last)

    # ========================================================================
    # UI
    # ========================================================================
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top bar
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
        self.btn_random.grid(row=0, column=2, padx=(0, 10), pady=10)

        self.btn_mode = ctk.CTkButton(
            self.top_frame, text="", width=110,
            font=("Roboto", 13), corner_radius=10, height=34,
            command=self._toggle_play_mode
        )
        self.btn_mode.grid(row=0, column=3, padx=(0, 10), pady=10)
        self._update_mode_button()

        self.btn_favorites = ctk.CTkButton(
            self.top_frame, text="♡  Favoritos", width=130,
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"], font=("Roboto", 13),
            border_color=COLORS["accent"], border_width=1,
            corner_radius=10, height=34,
            command=self._toggle_favorites_view
        )
        self.btn_favorites.grid(row=0, column=4, padx=(0, 12), pady=10)

        # Content
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, minsize=350)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Lista
        self.list_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"], border_width=1, corner_radius=16
        )
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.list_frame.grid_rowconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.list_frame,
            label_text="  📀  Biblioteca  (click derecho para opciones)  ",
            label_font=("Roboto", 16, "bold"),
            label_text_color=COLORS["text_primary"],
            label_fg_color=COLORS["bg_tertiary"],
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            border_color=COLORS["border"], border_width=0
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.list_widgets: list[tuple[ctk.CTkFrame, ctk.CTkLabel]] = []

        # Reproductor
        self.player_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"], border_width=1, corner_radius=16,
            width=350
        )
        self.player_frame.grid(row=0, column=1, sticky="ns")
        self.player_frame.grid_propagate(False)

        # --- ZONA FIJA: foto + nombre/artista ---
        self.display_frame = ctk.CTkFrame(
            self.player_frame, fg_color="transparent", height=480
        )
        self.display_frame.grid(row=0, column=0, sticky="new", padx=0, pady=0)
        self.display_frame.grid_propagate(False)

        self.cover_label = ctk.CTkLabel(
            self.display_frame, text="", fg_color="transparent"
        )
        self.cover_label.pack(pady=(20, 10))

        self.info_frame = ctk.CTkFrame(
            self.display_frame,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=12,
            width=310,
            height=110
        )
        self.info_frame.pack(pady=(0, 10))
        self.info_frame.pack_propagate(False)

        self.lbl_title = ctk.CTkLabel(
            self.info_frame,
            text="Sin reproducción",
            font=("Roboto", 18, "bold"),
            text_color=COLORS["text_primary"],
            wraplength=280
        )
        self.lbl_title.pack(pady=(12, 2))

        self.lbl_artist = ctk.CTkLabel(
            self.info_frame,
            text="Selecciona una carpeta",
            font=("Roboto", 13),
            text_color=COLORS["text_secondary"],
            wraplength=280
        )
        self.lbl_artist.pack(pady=(0, 12))

        # Controls
        self.controls_frame = ctk.CTkFrame(
            self.player_frame, fg_color="transparent"
        )
        self.controls_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.controls_frame.grid_columnconfigure(4, weight=1)

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
        self.btn_prev.grid(row=0, column=1, padx=6)

        self.btn_play = ctk.CTkButton(
            self.controls_frame, text="▶", width=70,
            fg_color=COLORS["accent_bright"], hover_color=COLORS["accent"],
            text_color=COLORS["bg_primary"], font=("Roboto", 18, "bold"),
            corner_radius=12, height=42,
            command=self._toggle_play
        )
        self.btn_play.grid(row=0, column=2, padx=8)

        self.btn_next = ctk.CTkButton(
            self.controls_frame, text="⏭", width=50, **btn_style,
            command=self._next_song
        )
        self.btn_next.grid(row=0, column=3, padx=6)

        # Progress
        self.progress_frame = ctk.CTkFrame(
            self.player_frame, fg_color="transparent"
        )
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 6))
        self.progress_frame.grid_columnconfigure(0, weight=0)
        self.progress_frame.grid_columnconfigure(1, weight=1)
        self.progress_frame.grid_columnconfigure(2, weight=0)

        self.lbl_time_current = ctk.CTkLabel(
            self.progress_frame, text="00:00",
            font=("Roboto", 12), text_color=COLORS["text_secondary"],
            width=42
        )
        self.lbl_time_current.grid(row=0, column=0, padx=(0, 8))

        self.progress = ctk.CTkSlider(
            self.progress_frame, from_=0, to=1000, state="disabled",
            fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent"],
            button_color=COLORS["accent_bright"], button_hover_color=COLORS["accent_hover"],
            height=16, corner_radius=8
        )
        self.progress.grid(row=0, column=1, sticky="ew")
        self.progress.bind("<ButtonPress-1>", lambda e: setattr(self, "_is_seeking", True))
        self.progress.bind("<ButtonRelease-1>", self._on_seek)

        self.lbl_time_total = ctk.CTkLabel(
            self.progress_frame, text="00:00",
            font=("Roboto", 12), text_color=COLORS["text_secondary"],
            width=42
        )
        self.lbl_time_total.grid(row=0, column=2, padx=(8, 0))

        # Volume
        self.vol_slider = ctk.CTkSlider(
            self.player_frame, from_=0, to=1,
            fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent_bright"],
            button_color=COLORS["accent"], button_hover_color=COLORS["accent_hover"],
            height=12, corner_radius=6,
            command=self._set_volume
        )
        self.vol_slider.set(self.config.config.get("volume", 0.7))
        self.vol_slider.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.player.set_volume(self.vol_slider.get())

        # Status
        self.status = ctk.CTkLabel(
            self, text="✦ Listo",
            font=("Roboto", 12), text_color=COLORS["text_secondary"],
            anchor="w", fg_color="transparent"
        )
        self.status.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 12))

        self._update_loop()

    # ========================================================================
    # FAVORITOS
    # ========================================================================
    def _toggle_favorites_view(self):
        self.showing_favorites = not self.showing_favorites
        if self.showing_favorites:
            self.btn_favorites.configure(
                text="♥  Favoritos",
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                border_color=COLORS["accent"],
            )
        else:
            self.btn_favorites.configure(
                text="♡  Favoritos",
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["accent"],
                border_color=COLORS["accent"],
            )
        self._apply_filters()

    def _toggle_favorite(self, filtered_idx: int):
        meta = self.filtered_songs[filtered_idx]
        is_fav = self.config.toggle_favorite(meta.path)
        self.status.configure(
            text=f"✦ {'♥ Añadido a' if is_fav else '♡ Quitado de'} favoritos"
        )
        if self.showing_favorites:
            self._apply_filters()
        else:
            self._update_list_appearance()

    # ========================================================================
    # MENÚ CONTEXTUAL
    # ========================================================================
    def _show_context_menu(self, event, filtered_idx: int):
        menu = Menu(self, tearoff=0, bg=COLORS["bg_secondary"],
                    fg=COLORS["text_primary"], activebackground=COLORS["accent"],
                    activeforeground=COLORS["text_primary"],
                    borderwidth=0, font=("Roboto", 11))

        meta = self.filtered_songs[filtered_idx]
        is_fav = self.config.is_favorite(meta.path)

        menu.add_command(label=f"▶  {meta.title[:40]}", state="disabled")
        menu.add_separator()
        menu.add_command(label="Reproducir ahora", command=lambda: self._select_song(filtered_idx))
        menu.add_command(label="⏭  Reproducir a continuación",
                         command=lambda: self._add_to_up_next(filtered_idx))
        menu.add_separator()
        menu.add_command(
            label=f"{'♥  Quitar de' if is_fav else '♡  Añadir a'} favoritos",
            command=lambda: self._toggle_favorite(filtered_idx)
        )

        if self.up_next:
            menu.add_separator()
            menu.add_command(label=f"En cola: {len(self.up_next)} tema(s)", state="disabled")

        menu.tk_popup(event.x_root, event.y_root)

    def _add_to_up_next(self, filtered_idx: int):
        meta = self.filtered_songs[filtered_idx]
        song_idx = self._song_path_to_idx.get(meta.path, -1)
        
        if song_idx == self.current_index:
            self.status.configure(text="✦ Ya está sonando")
            return
        if song_idx in self.up_next:
            self.status.configure(text="✦ Ya está en la cola")
            return
        
        self.up_next.append(song_idx)
        self.status.configure(text=f"✦ '{meta.title[:30]}' → a continuación")
        self._update_list_appearance()

    # ========================================================================
    # MODO
    # ========================================================================
    def _update_mode_button(self):
        if self.play_mode == "shuffle":
            self.btn_mode.configure(
                text="🔀  Aleatorio",
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["accent"],
                text_color=COLORS["text_primary"],
                border_color=COLORS["border"],
                border_width=1
            )
        else:
            self.btn_mode.configure(
                text="🔁  Cola",
                fg_color=COLORS["bg_tertiary"],
                hover_color=COLORS["accent"],
                text_color=COLORS["text_primary"],
                border_color=COLORS["border"],
                border_width=1
            )

    def _toggle_play_mode(self):
        self.play_mode = "shuffle" if self.play_mode == "queue" else "queue"
        self.config.config["play_mode"] = self.play_mode
        self._update_mode_button()
        self.status.configure(
            text=f"✦ Modo: {'Aleatorio' if self.play_mode == 'shuffle' else 'Cola'}"
        )

    # ========================================================================
    # HISTORIAL
    # ========================================================================
    def _add_to_history(self, index: int):
        if self.history_index < len(self.play_history) - 1:
            self.play_history = self.play_history[:self.history_index + 1]
        if not self.play_history or self.play_history[-1] != index:
            self.play_history.append(index)
            self.history_index = len(self.play_history) - 1

    # ========================================================================
    # ESTILOS DE FILA — Optimizados O(1)
    # ========================================================================
    def _get_row_state(self, song_idx: int) -> str:
        if song_idx == self.current_index:
            return "playing"
        if song_idx in self.up_next:
            return "up_next"
        return "normal"

    def _apply_row_style(self, row: ctk.CTkFrame, lbl: ctk.CTkLabel, state: str, hover: bool = False):
        if state == "playing":
            bg = COLORS["accent_hover"] if hover else COLORS["accent"]
            border = COLORS["border"]
            bw = 1
        elif state == "up_next":
            bg = COLORS["accent"] if hover else COLORS["bg_tertiary"]
            border = COLORS["accent_bright"]
            bw = 2
        else:
            bg = COLORS["accent"] if hover else COLORS["bg_tertiary"]
            border = COLORS["border"]
            bw = 1
        
        row.configure(fg_color=bg, border_color=border, border_width=bw)
        lbl.configure(text_color=COLORS["text_primary"])

    def _on_row_enter(self, event, row: ctk.CTkFrame, lbl: ctk.CTkLabel):
        if getattr(row, "_hover", False):
            return
        row._hover = True
        state = self._get_row_state(getattr(row, "song_idx", -1))
        self._apply_row_style(row, lbl, state, hover=True)

    def _on_row_leave(self, event, row: ctk.CTkFrame, lbl: ctk.CTkLabel):
        row._hover = False
        self.after(5, lambda: self._do_row_leave(row, lbl))

    def _do_row_leave(self, row: ctk.CTkFrame, lbl: ctk.CTkLabel):
        if not getattr(row, "_hover", False):
            state = self._get_row_state(getattr(row, "song_idx", -1))
            self._apply_row_style(row, lbl, state, hover=False)

    def _update_list_appearance(self):
        """Solo cambia colores y texto. NUNCA destruye widgets."""
        for idx, (row, lbl) in enumerate(self.list_widgets):
            if idx < len(self.filtered_songs):
                meta = self.filtered_songs[idx]
                heart = "♥ " if self.config.is_favorite(meta.path) else ""
                lbl.configure(text=f"{heart}{meta.title}  —  {meta.artist}  ({meta.format_duration()})")
                
                song_idx = self._song_path_to_idx.get(meta.path, -1)
                row.song_idx = song_idx
                state = self._get_row_state(song_idx)
                
                self._apply_row_style(row, lbl, state, hover=False)
                row.grid()
            else:
                row.grid_remove()

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
        self.filtered_songs.clear()
        self.play_history.clear()
        self.up_next.clear()
        self.history_index = -1
        self._error_count = 0
        self.current_index = -1
        
        path = Path(folder)
        for f in sorted(path.rglob("*")):
            if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.songs.append(AudioMetadata(str(f)))

        self._song_path_to_idx = {meta.path: i for i, meta in enumerate(self.songs)}
        
        self._apply_filters()
        self._rebuild_list()
        self.status.configure(text=f"✦ {len(self.songs)} canciones cargadas")

    def _rebuild_list(self):
        """ÚNICO lugar donde se destruyen y recrean widgets. Solo al cargar carpeta."""
        for row, lbl in self.list_widgets:
            row.destroy()
        self.list_widgets.clear()

        for idx, meta in enumerate(self.filtered_songs):
            row = ctk.CTkFrame(
                self.scroll_frame,
                fg_color=COLORS["bg_tertiary"],
                corner_radius=8,
                border_color=COLORS["border"], border_width=1,
                cursor="hand2"
            )
            row.grid(sticky="ew", pady=3, padx=2)
            row.grid_columnconfigure(0, weight=1)

            lbl = ctk.CTkLabel(
                row,
                text=f"{meta.title}  —  {meta.artist}  ({meta.format_duration()})",
                anchor="w", font=("Roboto", 12),
                text_color=COLORS["text_primary"],
                cursor="hand2"
            )
            lbl.grid(row=0, column=0, sticky="nsew", padx=12, pady=10)

            song_idx = self._song_path_to_idx.get(meta.path, -1)
            row.song_idx = song_idx

            row.bind("<Button-1>", lambda e, i=idx: self._select_song(i))
            lbl.bind("<Button-1>", lambda e, i=idx: self._select_song(i))

            row.bind("<Button-3>", lambda e, i=idx: self._show_context_menu(e, i))
            lbl.bind("<Button-3>", lambda e, i=idx: self._show_context_menu(e, i))

            row.bind("<Enter>", lambda e, r=row, l=lbl: self._on_row_enter(e, r, l))
            row.bind("<Leave>", lambda e, r=row, l=lbl: self._on_row_leave(e, r, l))
            lbl.bind("<Enter>", lambda e, r=row, l=lbl: self._on_row_enter(e, r, l))
            lbl.bind("<Leave>", lambda e, r=row, l=lbl: self._on_row_leave(e, r, l))

            self.list_widgets.append((row, lbl))

        self._update_list_appearance()

    # ========================================================================
    # BÚSQUEDA + FAVORITOS — Con debounce, NO reconstruye
    # ========================================================================
    def _on_search(self, event=None):
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(200, self._apply_filters)

    def _apply_filters(self):
        self._search_after_id = None
        query = self.search_entry.get().lower()
        base = self.songs.copy()

        if self.showing_favorites:
            base = [s for s in base if self.config.is_favorite(s.path)]

        if not query:
            self.filtered_songs = base
        else:
            self.filtered_songs = [
                s for s in base
                if query in s.title.lower()
                or query in s.artist.lower()
                or query in s.album.lower()
            ]
        self._update_list_appearance()

    # ========================================================================
    # REPRODUCCIÓN
    # ========================================================================
    def _select_song(self, filtered_idx: int):
        if not self.filtered_songs:
            return
        meta = self.filtered_songs[filtered_idx]
        song_idx = self._song_path_to_idx.get(meta.path, -1)
        if song_idx < 0:
            return
        self.current_index = song_idx
        self._add_to_history(self.current_index)
        self._play_current(direction=1)

    def _play_current(self, direction: int = 1):
        if self.current_index < 0 or self.current_index >= len(self.songs):
            return
        meta = self.songs[self.current_index]

        try:
            self.player.load(meta.path)
            self.player.play()
            self._error_count = 0
        except Exception as e:
            self._error_count += 1
            self.status.configure(text=f"✦ Error ({self._error_count}): {str(e)[:50]}")
            if self._error_count >= 5:
                self.status.configure(text="✦ Demasiados errores, detenido")
                return
            if direction == -1:
                self.after(200, self._prev_song)
            else:
                self.after(200, self._next_song)
            return

        self.lbl_title.configure(text=meta.title)
        self.lbl_artist.configure(text=meta.artist)

        img = self.cover_gen.get_image(meta)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(280, 280))
        self.cover_label.configure(image=ctk_img, text="")
        self.cover_label.image = ctk_img  # type: ignore[attr-defined]

        self.btn_play.configure(text="⏸")
        self.progress.configure(state="normal")
        self.status.configure(text="✦ Reproduciendo")

        self._update_list_appearance()

    def _toggle_play(self):
        if not self.player.has_file():
            if self.songs:
                self.current_index = 0
                self._add_to_history(self.current_index)
                self._play_current(direction=1)
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
        if self.play_mode == "shuffle":
            if self.history_index > 0:
                self.history_index -= 1
                self.current_index = self.play_history[self.history_index]
                self._play_current(direction=-1)
        else:
            self.current_index = (self.current_index - 1) % len(self.songs)
            self._add_to_history(self.current_index)
            self._play_current(direction=-1)

    def _next_song(self):
        if not self.songs:
            return
        
        if self.up_next:
            self.current_index = self.up_next.pop(0)
            self._add_to_history(self.current_index)
            self._play_current(direction=1)
            return
        
        if self.play_mode == "shuffle":
            if self.history_index < len(self.play_history) - 1:
                self.history_index += 1
                self.current_index = self.play_history[self.history_index]
            else:
                self.current_index = random.randint(0, len(self.songs) - 1)
                self._add_to_history(self.current_index)
            self._play_current(direction=1)
        else:
            self.current_index = (self.current_index + 1) % len(self.songs)
            self._add_to_history(self.current_index)
            self._play_current(direction=1)

    def _play_random(self):
        if not self.songs:
            return
        self.current_index = random.randint(0, len(self.songs) - 1)
        self._add_to_history(self.current_index)
        self._play_current(direction=0)

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

            self.lbl_time_current.configure(text=self._fmt(pos))
            self.lbl_time_total.configure(text=self._fmt(dur))

            if dur > 0:
                self.progress.set(int((pos / dur) * 1000))

            if self.player.is_finished() and not self.player.is_paused():
                self._next_song()

        self.after_id = self.after(100, self._update_loop)

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