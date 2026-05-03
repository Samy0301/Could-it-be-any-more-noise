"""Interfaz gráfica de SonicVault usando CustomTkinter."""
import random
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from config import AppConfig
from metadata import AudioMetadata, SUPPORTED_EXTS
from player import MusicPlayer
from utils import CoverGenerator

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")


class SongRow(ctk.CTkFrame):
    """Fila individual de la biblioteca con hover y estado activo."""

    def __init__(self, master, index: int, meta: AudioMetadata, is_fav: bool,
                 on_select, on_fav_toggle, **kwargs):
        super().__init__(master, **kwargs)
        self.index = index
        self.meta = meta
        self._on_select = on_select
        self._on_fav_toggle = on_fav_toggle
        self._active = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)

        # Texto principal
        self.lbl = ctk.CTkLabel(
            self,
            text=f"{meta.title}  —  {meta.artist}  ({meta.formatted_duration})",
            anchor="w",
            font=("Roboto", 13),
        )
        self.lbl.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=10)
        self.lbl.bind("<Button-1>", lambda e: self._on_select(self.index))

        # Botón favorito
        fav_text = "★" if is_fav else "☆"
        self.btn_fav = ctk.CTkButton(
            self,
            text=fav_text,
            width=32,
            height=32,
            font=("Roboto", 16),
            fg_color="transparent",
            hover_color=("#e0e0e0", "#2a2a4a"),
            text_color=("#f39c12", "#f1c40f"),
            command=self._toggle_fav,
        )
        self.btn_fav.grid(row=0, column=1, padx=(0, 8), pady=8)

        # Eventos de click en toda la fila
        for widget in (self, self.lbl):
            widget.bind("<Button-1>", lambda e: self._on_select(self.index))
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

        self._set_normal()

    def _set_normal(self):
        if self._active:
            self.configure(fg_color=("#3b82f6", "#2563eb"))
            self.lbl.configure(text_color="white")
        else:
            self.configure(fg_color=("transparent", "transparent"))
            self.lbl.configure(text_color=("gray10", "gray90"))

    def _on_enter(self, _event=None):
        if not self._active:
            self.configure(fg_color=("#e5e7eb", "#1e1e3f"))

    def _on_leave(self, _event=None):
        self._set_normal()

    def set_active(self, active: bool):
        self._active = active
        self._set_normal()

    def _toggle_fav(self):
        is_fav = self._on_fav_toggle(self.meta.path)
        self.btn_fav.configure(text="★" if is_fav else "☆")

    def update_fav_state(self, is_fav: bool):
        self.btn_fav.configure(text="★" if is_fav else "☆")


class SonicVaultApp(ctk.CTk):
    """Ventana principal de SonicVault."""

    def __init__(self):
        super().__init__()
        self.config_app = AppConfig()
        self.player = MusicPlayer()
        self.cover_gen = CoverGenerator((280, 280))

        self.songs: list[AudioMetadata] = []
        self.filtered_songs: list[AudioMetadata] = []
        self.current_index: int = -1
        self._is_seeking: bool = False
        self._after_id: str | None = None

        self._setup_window()
        self._build_ui()
        self._bind_events()
        self._restore_session()
        self._start_update_loop()

    # ------------------------------------------------------------------
    # Configuración de ventana
    # ------------------------------------------------------------------
    def _setup_window(self):
        self.title("SonicVault 🎵")
        self.geometry(self.config_app.window_size)
        self.minsize(950, 650)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _restore_session(self):
        last = self.config_app.last_folder
        if last and Path(last).exists():
            self._load_folder(last)

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ===== BARRA SUPERIOR =====
        top = ctk.CTkFrame(self, height=60)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        top.grid_propagate(False)
        top.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            top,
            placeholder_text="🔍  Buscar canción, artista o álbum…",
            font=("Roboto", 14),
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(10, 10), pady=12)

        self.btn_folder = ctk.CTkButton(
            top, text="📁  Abrir carpeta", width=130, command=self._select_folder
        )
        self.btn_folder.grid(row=0, column=1, padx=(0, 8), pady=12)

        self.btn_fav_filter = ctk.CTkButton(
            top,
            text="⭐  Solo favoritos",
            width=130,
            command=self._toggle_fav_filter,
            fg_color=("#6b7280", "#4b5563"),
        )
        self.btn_fav_filter.grid(row=0, column=2, padx=(0, 8), pady=12)

        self.btn_random = ctk.CTkButton(
            top, text="🎲  Aleatorio", width=110, command=self._play_random
        )
        self.btn_random.grid(row=0, column=3, padx=(0, 10), pady=12)

        # ===== CONTENIDO =====
        content = ctk.CTkFrame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        content.grid_columnconfigure(0, weight=2, minsize=320)
        content.grid_columnconfigure(1, weight=3, minsize=400)
        content.grid_rowconfigure(0, weight=1)

        # -- Izquierda: Reproductor --
        self._build_player_panel(content)
        # -- Derecha: Biblioteca --
        self._build_library_panel(content)

        # ===== BARRA DE ESTADO =====
        self.status = ctk.CTkLabel(self, text="Listo", anchor="w", font=("Roboto", 12))
        self.status.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))

    def _build_player_panel(self, parent):
        left = ctk.CTkFrame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=0)
        left.grid_rowconfigure(2, weight=0)
        left.grid_rowconfigure(3, weight=0)
        left.grid_columnconfigure(0, weight=1)

        # Carátula
        self.cover_label = ctk.CTkLabel(left, text="")
        self.cover_label.grid(row=0, column=0, padx=20, pady=20, sticky="n")

        # Info
        info = ctk.CTkFrame(left)
        info.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))

        self.lbl_title = ctk.CTkLabel(
            info, text="Sin reproducción", font=("Roboto", 18, "bold"), wraplength=280
        )
        self.lbl_title.pack(pady=(12, 2))

        self.lbl_artist = ctk.CTkLabel(
            info, text="Abre una carpeta para comenzar", font=("Roboto", 14), text_color="gray"
        )
        self.lbl_artist.pack(pady=(0, 2))

        self.lbl_album = ctk.CTkLabel(
            info, text="", font=("Roboto", 12), text_color="gray70"
        )
        self.lbl_album.pack(pady=(0, 10))

        # Favorito global
        self.btn_fav_global = ctk.CTkButton(
            info,
            text="☆  Añadir a favoritos",
            width=180,
            fg_color="transparent",
            border_width=1,
            border_color=("#d1d5db", "#4b5563"),
            command=self._toggle_global_fav,
        )
        self.btn_fav_global.pack(pady=(0, 10))
        self.btn_fav_global.configure(state="disabled")

        # Controles
        ctrl = ctk.CTkFrame(left)
        ctrl.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 8))

        self.btn_prev = ctk.CTkButton(ctrl, text="⏮", width=45, font=("Roboto", 16), command=self._prev_song)
        self.btn_prev.pack(side="left", padx=(8, 4))

        self.btn_play = ctk.CTkButton(ctrl, text="▶", width=60, font=("Roboto", 18), command=self._toggle_play)
        self.btn_play.pack(side="left", padx=4)

        self.btn_next = ctk.CTkButton(ctrl, text="⏭", width=45, font=("Roboto", 16), command=self._next_song)
        self.btn_next.pack(side="left", padx=(4, 8))

        # Progreso
        prog_frame = ctk.CTkFrame(left, fg_color="transparent")
        prog_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 4))
        prog_frame.grid_columnconfigure(0, weight=1)

        self.lbl_time = ctk.CTkLabel(prog_frame, text="00:00 / 00:00", font=("Roboto", 12))
        self.lbl_time.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.progress = ctk.CTkSlider(prog_frame, from_=0, to=1000, state="disabled")
        self.progress.grid(row=0, column=1, sticky="ew", padx=8)
        self.progress.bind("<ButtonPress-1>", lambda e: setattr(self, "_is_seeking", True))
        self.progress.bind("<ButtonRelease-1>", self._on_seek)

        # Volumen
        vol_frame = ctk.CTkFrame(left, fg_color="transparent")
        vol_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 15))
        vol_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(vol_frame, text="🔊", font=("Roboto", 14)).grid(row=0, column=0, padx=(0, 6))
        self.vol_slider = ctk.CTkSlider(vol_frame, from_=0, to=1, command=self._set_volume)
        self.vol_slider.set(self.config_app.volume)
        self.vol_slider.grid(row=0, column=1, sticky="ew")
        self.player.set_volume(self.config_app.volume)

    def _build_library_panel(self, parent):
        right = ctk.CTkFrame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=1)
        right.grid_columnconfigure(0, weight=1)

        self.scroll_frame = ctk.CTkScrollableFrame(right, label_text="📚  Biblioteca")
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.list_rows: list[SongRow] = []

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def _bind_events(self):
        self.search_entry.bind("<KeyRelease>", lambda e: self._apply_filter())
        self.bind("<space>", lambda e: self._toggle_play())
        self.bind("<Left>", lambda e: self._prev_song())
        self.bind("<Right>", lambda e: self._next_song())

    # ------------------------------------------------------------------
    # Biblioteca
    # ------------------------------------------------------------------
    def _select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self._load_folder(folder)

    def _load_folder(self, folder: str):
        self.config_app.last_folder = folder
        self.status.configure(text=f"Cargando: {folder}")
        self.update_idletasks()

        self.songs.clear()
        path = Path(folder)
        for f in sorted(path.rglob("*")):
            if f.suffix.lower() in SUPPORTED_EXTS:
                try:
                    self.songs.append(AudioMetadata(str(f)))
                except Exception:
                    continue

        self._apply_filter()
        self.status.configure(text=f"{len(self.songs)} canciones cargadas")

    def _apply_filter(self):
        query = self.search_entry.get().lower().strip()
        show_fav = self.config_app.show_favorites_only

        self.filtered_songs = []
        for s in self.songs:
            if show_fav and not self.config_app.is_favorite(s.path):
                continue
            if query and query not in s.title.lower() and query not in s.artist.lower() and query not in s.album.lower():
                continue
            self.filtered_songs.append(s)

        self._render_list()

    def _render_list(self):
        for row in self.list_rows:
            row.destroy()
        self.list_rows.clear()

        for idx, meta in enumerate(self.filtered_songs):
            row = SongRow(
                self.scroll_frame,
                index=idx,
                meta=meta,
                is_fav=self.config_app.is_favorite(meta.path),
                on_select=self._select_song,
                on_fav_toggle=self._on_fav_toggle,
                corner_radius=8,
            )
            row.grid(sticky="ew", pady=3)
            self.list_rows.append(row)

        self._highlight_active()

    def _highlight_active(self):
        if self.current_index < 0:
            return
        try:
            current_meta = self.songs[self.current_index]
        except IndexError:
            return
        for row in self.list_rows:
            row.set_active(row.meta.path == current_meta.path)

    def _toggle_fav_filter(self):
        self.config_app.show_favorites_only = not self.config_app.show_favorites_only
        text = "⭐  Solo favoritos" if self.config_app.show_favorites_only else "☆  Toda la biblioteca"
        self.btn_fav_filter.configure(text=text)
        self._apply_filter()

    def _on_fav_toggle(self, path: str) -> bool:
        is_fav = self.config_app.toggle_favorite(path)
        self._update_fav_buttons()
        return is_fav

    def _update_fav_buttons(self):
        # Actualiza botón global
        if self.current_index >= 0:
            meta = self.songs[self.current_index]
            is_fav = self.config_app.is_favorite(meta.path)
            self.btn_fav_global.configure(
                text="★  Quitar de favoritos" if is_fav else "☆  Añadir a favoritos"
            )
        # Actualiza filas visibles
        for row in self.list_rows:
            row.update_fav_state(self.config_app.is_favorite(row.meta.path))

    def _toggle_global_fav(self):
        if self.current_index < 0:
            return
        self._on_fav_toggle(self.songs[self.current_index].path)

    # ------------------------------------------------------------------
    # Reproducción
    # ------------------------------------------------------------------
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
            self.status.configure(text=f"Error: {str(e)[:60]}")
            self.after(1500, self._next_song)
            return

        self.lbl_title.configure(text=meta.title)
        self.lbl_artist.configure(text=meta.artist)
        self.lbl_album.configure(text=f"{meta.album}  •  {meta.formatted_duration}")

        img = self.cover_gen.get_image(meta.cover)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(280, 280))
        self.cover_label.configure(image=ctk_img, text="")
        self.cover_label.image = ctk_img  # evitar GC

        self.btn_play.configure(text="⏸")
        self.progress.configure(state="normal")
        self.btn_fav_global.configure(state="normal")
        self._update_fav_buttons()
        self._highlight_active()
        self.status.configure(text="Reproduciendo")

    def _toggle_play(self):
        if not self.player.has_file():
            if self.songs:
                self.current_index = 0
                self._play_current()
            return
        if self.player.is_playing:
            self.player.pause()
            self.btn_play.configure(text="▶")
            self.status.configure(text="Pausado")
        else:
            self.player.resume()
            self.btn_play.configure(text="⏸")
            self.status.configure(text="Reproduciendo")

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
        self.config_app.volume = vol

    def _on_seek(self, _event=None):
        self._is_seeking = False
        if self.current_index >= 0 and self.songs:
            ratio = self.progress.get() / 1000
            seconds = self.songs[self.current_index].duration * ratio
            self.player.seek(seconds)

    # ------------------------------------------------------------------
    # Loop de actualización
    # ------------------------------------------------------------------
    def _start_update_loop(self):
        self._update_loop()

    def _update_loop(self):
        if self.current_index >= 0 and self.songs and not self._is_seeking:
            pos = self.player.position
            dur = self.songs[self.current_index].duration

            self.lbl_time.configure(text=f"{self._fmt(pos)} / {self._fmt(dur)}")
            if dur > 0:
                self.progress.set(int((pos / dur) * 1000))

            if self.player.is_finished and not self.player.is_paused:
                self._next_song()

        self._after_id = self.after(500, self._update_loop)

    @staticmethod
    def _fmt(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------
    def _on_close(self):
        self.config_app.window_size = f"{self.winfo_width()}x{self.winfo_height()}"
        self.config_app.save()
        if self._after_id:
            self.after_cancel(self._after_id)
        self.player.stop()
        self.destroy()
