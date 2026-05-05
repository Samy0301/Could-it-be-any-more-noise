#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SonicVault 🎵 — Drag & Drop con tracking correcto del tema en reproducción
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
        self.current_index = -1          # Índice en self.songs del tema SONANDO
        self.current_filtered_index = -1 # Índice en self.filtered_songs del tema SONANDO
        self.after_id = None
        self._is_seeking = False

        self.play_history: list[int] = []  # Guarda índices de self.songs
        self.history_index = -1
        self._error_count = 0

        self.play_mode = self.config.config.get("play_mode", "queue")

        # Drag & Drop
        self._drag_start_y = 0
        self._drag_start_index = -1
        self._drag_active = False
        self._drag_moved = False

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
    # CONSTRUCCIÓN DE UI
    # ========================================================================
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ----- TOP BAR -----
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
        self.btn_mode.grid(row=0, column=3, padx=(0, 12), pady=10)
        self._update_mode_button()

        # ----- CONTENT -----
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, minsize=350)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # -- Izquierda: Lista --
        self.list_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"], border_width=1, corner_radius=16
        )
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.list_frame.grid_rowconfigure(0, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.list_frame,
            label_text="  📀  Biblioteca  (arrastra para ordenar)  ",
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

        # -- Derecha: Reproductor --
        self.player_frame = ctk.CTkFrame(
            self.content_frame, fg_color=COLORS["bg_secondary"],
            border_color=COLORS["border"], border_width=1, corner_radius=16,
            width=350
        )
        self.player_frame.grid(row=0, column=1, sticky="ns")
        self.player_frame.grid_propagate(False)
        self.player_frame.grid_rowconfigure(0, weight=1)
        self.player_frame.grid_rowconfigure(1, weight=0)

        # Portada
        self.cover_label = ctk.CTkLabel(
            self.player_frame, text="", fg_color="transparent"
        )
        self.cover_label.grid(row=0, column=0, padx=35, pady=20, sticky="n")

        # Info
        self.info_frame = ctk.CTkFrame(
            self.player_frame, fg_color=COLORS["bg_tertiary"],
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
            self.player_frame, fg_color="transparent"
        )
        self.controls_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
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
        self.progress_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 6))
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
        self.vol_slider.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 15))
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
    # DRAG & DROP
    # ========================================================================
    def _get_widget_index_at_y(self, y: int) -> int:
        if not self.list_widgets:
            return -1
        
        scroll_y = self.scroll_frame.winfo_rooty()
        relative_y = y - scroll_y
        
        best_idx = 0
        best_dist = float('inf')
        
        for idx, (row, _) in enumerate(self.list_widgets):
            row_y = row.winfo_y()
            row_h = row.winfo_height()
            center = row_y + row_h // 2
            dist = abs(relative_y - center)
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        
        return best_idx

    def _on_drag_press(self, event, index: int):
        self._drag_start_y = event.y_root
        self._drag_start_index = index
        self._drag_active = True
        self._drag_moved = False

    def _on_drag_motion(self, event):
        if not self._drag_active:
            return
        
        delta = abs(event.y_root - self._drag_start_y)
        if delta > 5 and not self._drag_moved:
            self._drag_moved = True
            # Visual de arrastre: borde brillante, NO cambiar highlight de reproducción
            if 0 <= self._drag_start_index < len(self.list_widgets):
                row, lbl = self.list_widgets[self._drag_start_index]
                # Solo si NO es el que está reproduciendo
                if self._drag_start_index != self.current_filtered_index:
                    row.configure(
                        fg_color=COLORS["bg_tertiary"],
                        border_color=COLORS["accent_bright"],
                        border_width=2
                    )

    def _on_drag_release(self, event):
        if not self._drag_active:
            return
        
        if self._drag_moved and self._drag_start_index != -1:
            target_idx = self._get_widget_index_at_y(event.y_root)
            
            if target_idx != -1 and target_idx != self._drag_start_index:
                self._move_item(self._drag_start_index, target_idx)
                self.status.configure(
                    text=f"✦ Movido a posición {target_idx + 1}"
                )
        
        self._drag_active = False
        self._drag_moved = False
        self._drag_start_index = -1
        # Solo actualizar estilos, NO destruir widgets
        self._update_list_appearance()

    def _move_item(self, from_idx: int, to_idx: int):
        """Mueve un elemento y actualiza el índice del tema en reproducción."""
        if from_idx == to_idx:
            return
        
        # Guardar qué tema está sonando antes de mover
        playing_path = None
        if 0 <= self.current_filtered_index < len(self.filtered_songs):
            playing_path = self.filtered_songs[self.current_filtered_index].path
        
        # Mover en filtered_songs
        item = self.filtered_songs.pop(from_idx)
        self.filtered_songs.insert(to_idx, item)
        
        # Recalcular dónde quedó el tema que sonaba
        if playing_path:
            for i, s in enumerate(self.filtered_songs):
                if s.path == playing_path:
                    self.current_filtered_index = i
                    break
        
        # Sincronizar con songs
        self._sync_songs_from_filtered()

    def _sync_songs_from_filtered(self):
        """Reordena songs según filtered y actualiza current_index."""
        filtered_paths = {s.path: i for i, s in enumerate(self.filtered_songs)}
        self.songs.sort(key=lambda s: filtered_paths.get(s.path, 999999))
        
        # Actualizar current_index al nuevo índice en songs del tema sonando
        if 0 <= self.current_filtered_index < len(self.filtered_songs):
            playing_path = self.filtered_songs[self.current_filtered_index].path
            for i, s in enumerate(self.songs):
                if s.path == playing_path:
                    self.current_index = i
                    break

    # ========================================================================
    # MODO DE REPRODUCCIÓN
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
    # ESTILOS DE LISTA / HIGHLIGHT (sin destruir widgets)
    # ========================================================================
    def _set_row_style(self, row: ctk.CTkFrame, lbl: ctk.CTkLabel, is_playing: bool, is_dragging: bool = False):
        row.is_playing = is_playing
        if is_dragging:
            # Visual de arrastre: borde brillante
            row.configure(
                fg_color=COLORS["bg_tertiary"],
                border_color=COLORS["accent_bright"],
                border_width=2
            )
        elif is_playing:
            # Visual de reproducción: fondo acento
            row.configure(
                fg_color=COLORS["accent"],
                border_color=COLORS["border"],
                border_width=1
            )
        else:
            # Normal
            row.configure(
                fg_color=COLORS["bg_tertiary"],
                border_color=COLORS["border"],
                border_width=1
            )
        lbl.configure(text_color=COLORS["text_primary"])

    def _on_row_enter(self, row: ctk.CTkFrame, lbl: ctk.CTkLabel):
        # No cambiar hover si está arrastrando
        if self._drag_active:
            return
        if getattr(row, "is_playing", False):
            row.configure(fg_color=COLORS["accent_hover"])
        else:
            row.configure(fg_color=COLORS["accent"])

    def _on_row_leave(self, row: ctk.CTkFrame, lbl: ctk.CTkLabel):
        # No cambiar hover si está arrastrando
        if self._drag_active:
            return
        if getattr(row, "is_playing", False):
            row.configure(fg_color=COLORS["accent"])
        else:
            row.configure(fg_color=COLORS["bg_tertiary"])

    def _update_list_appearance(self):
        """Actualiza texto, colores y tracking del tema en reproducción."""
        # Recalcular current_filtered_index basado en current_index
        if 0 <= self.current_index < len(self.songs):
            playing_path = self.songs[self.current_index].path
            for i, s in enumerate(self.filtered_songs):
                if s.path == playing_path:
                    self.current_filtered_index = i
                    break
        
        for idx, (row, lbl) in enumerate(self.list_widgets):
            if idx < len(self.filtered_songs):
                meta = self.filtered_songs[idx]
                lbl.configure(
                    text=f"{meta.title}  —  {meta.artist}  ({meta.format_duration()})"
                )
                row.meta_path = meta.path
                is_playing = (idx == self.current_filtered_index)
                self._set_row_style(row, lbl, is_playing=is_playing)
                row.grid()
            else:
                row.grid_remove()

    # ========================================================================
    # CARPETA Y LISTA (construcción lazy)
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
        self.history_index = -1
        self._error_count = 0
        self.current_index = -1
        self.current_filtered_index = -1
        
        path = Path(folder)
        for f in sorted(path.rglob("*")):
            if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                self.songs.append(AudioMetadata(str(f)))

        self.filtered_songs = self.songs.copy()
        self._rebuild_list()
        self.status.configure(text=f"✦ {len(self.songs)} canciones cargadas")

    def _rebuild_list(self):
        """Destruye y reconstruye la lista. Usar solo al cargar carpeta."""
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
            row.meta_path = meta.path

            lbl = ctk.CTkLabel(
                row,
                text=f"{meta.title}  —  {meta.artist}  ({meta.format_duration()})",
                anchor="w", font=("Roboto", 12),
                text_color=COLORS["text_primary"]
            )
            lbl.grid(row=0, column=0, sticky="w", padx=12, pady=10)

            # Click simple
            row.bind("<ButtonRelease-1>", lambda e, i=idx: self._on_row_release(e, i))
            lbl.bind("<ButtonRelease-1>", lambda e, i=idx: self._on_row_release(e, i))

            # Hover
            row.bind("<Enter>", lambda e, r=row, l=lbl: self._on_row_enter(r, l))
            row.bind("<Leave>", lambda e, r=row, l=lbl: self._on_row_leave(r, l))
            lbl.bind("<Enter>", lambda e, r=row, l=lbl: self._on_row_enter(r, l))
            lbl.bind("<Leave>", lambda e, r=row, l=lbl: self._on_row_leave(r, l))

            # Drag bindings
            row.bind("<ButtonPress-1>", lambda e, i=idx: self._on_drag_press(e, i))
            row.bind("<B1-Motion>", self._on_drag_motion)
            lbl.bind("<ButtonPress-1>", lambda e, i=idx: self._on_drag_press(e, i))
            lbl.bind("<B1-Motion>", self._on_drag_motion)

            self.list_widgets.append((row, lbl))

        self._update_list_appearance()

    def _on_row_release(self, event, idx: int):
        if self._drag_moved:
            return
        self._select_song(idx)

    def _setup_global_drag(self):
        self.bind_all("<ButtonRelease-1>", lambda e: self._on_drag_release(e))

    # ========================================================================
    # BÚSQUEDA (solo filtra, no reconstruye)
    # ========================================================================
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
        self._update_list_appearance()

    # ========================================================================
    # REPRODUCCIÓN
    # ========================================================================
    def _select_song(self, filtered_idx: int):
        if not self.filtered_songs:
            return
        meta = self.filtered_songs[filtered_idx]
        try:
            self.current_index = self.songs.index(meta)
            self.current_filtered_index = filtered_idx
        except ValueError:
            return
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
        self.lbl_album.configure(text=f"{meta.album}  •  {meta.format_duration()}")

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
                self.current_filtered_index = 0
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
                # Recalcular current_filtered_index
                playing_path = self.songs[self.current_index].path
                for i, s in enumerate(self.filtered_songs):
                    if s.path == playing_path:
                        self.current_filtered_index = i
                        break
                self._play_current(direction=-1)
        else:
            self.current_index = (self.current_index - 1) % len(self.songs)
            self._add_to_history(self.current_index)
            # Recalcular current_filtered_index
            playing_path = self.songs[self.current_index].path
            for i, s in enumerate(self.filtered_songs):
                if s.path == playing_path:
                    self.current_filtered_index = i
                    break
            self._play_current(direction=-1)

    def _next_song(self):
        if not self.songs:
            return
        if self.play_mode == "shuffle":
            if self.history_index < len(self.play_history) - 1:
                self.history_index += 1
                self.current_index = self.play_history[self.history_index]
            else:
                self.current_index = random.randint(0, len(self.songs) - 1)
                self._add_to_history(self.current_index)
            # Recalcular current_filtered_index
            playing_path = self.songs[self.current_index].path
            for i, s in enumerate(self.filtered_songs):
                if s.path == playing_path:
                    self.current_filtered_index = i
                    break
            self._play_current(direction=1)
        else:
            self.current_index = (self.current_index + 1) % len(self.songs)
            self._add_to_history(self.current_index)
            # Recalcular current_filtered_index
            playing_path = self.songs[self.current_index].path
            for i, s in enumerate(self.filtered_songs):
                if s.path == playing_path:
                    self.current_filtered_index = i
                    break
            self._play_current(direction=1)

    def _play_random(self):
        if not self.songs:
            return
        self.current_index = random.randint(0, len(self.songs) - 1)
        self._add_to_history(self.current_index)
        # Recalcular current_filtered_index
        playing_path = self.songs[self.current_index].path
        for i, s in enumerate(self.filtered_songs):
            if s.path == playing_path:
                self.current_filtered_index = i
                break
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
    app._setup_global_drag()
    app.mainloop()