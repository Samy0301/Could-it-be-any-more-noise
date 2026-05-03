"""Reproductor de audio en streaming con soundfile + sounddevice."""
import threading
import soundfile as sf
import sounddevice as sd
import numpy as np


class MusicPlayer:
    """Reproduce audio en tiempo real sin cargar todo el archivo en RAM."""

    def __init__(self):
        self._sf: sf.SoundFile | None = None
        self._stream: sd.OutputStream | None = None
        self._lock = threading.Lock()

        self._samplerate: int = 44100
        self._channels: int = 2
        self._total_frames: int = 0
        self._current_frame: int = 0

        self._volume: float = 0.7
        self._paused: bool = False
        self._stop_flag: bool = False
        self._finished: bool = False

    # ------------------------------------------------------------------
    # Carga y reproducción
    # ------------------------------------------------------------------
    def load(self, filepath: str):
        """Abre el archivo en modo streaming."""
        self.stop()
        try:
            self._sf = sf.SoundFile(filepath, "r")
            self._samplerate = self._sf.samplerate
            self._channels = self._sf.channels
            self._total_frames = len(self._sf)
            self._current_frame = 0
            self._finished = False
            self._stop_flag = False
            self._paused = False
        except Exception:
            self._sf = None
            raise

    def play(self):
        """Inicia el stream de salida."""
        if self._sf is None or self._stream is not None:
            return
        self._stop_flag = False
        self._paused = False
        self._finished = False
        self._stream = sd.OutputStream(
            samplerate=self._samplerate,
            channels=self._channels,
            dtype="float32",
            callback=self._callback,
            blocksize=2048,
        )
        self._stream.start()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def toggle_pause(self):
        self._paused = not self._paused

    def stop(self):
        """Detiene stream, cierra archivo y resetea estado."""
        self._stop_flag = True
        self._paused = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        with self._lock:
            self._current_frame = 0
            self._finished = False
            if self._sf is not None:
                try:
                    self._sf.close()
                except Exception:
                    pass
                self._sf = None

    # ------------------------------------------------------------------
    # Callback interno (thread de audio)
    # ------------------------------------------------------------------
    def _callback(self, outdata, frames, time_info, status):
        if self._stop_flag or self._sf is None:
            outdata[:] = 0
            return

        with self._lock:
            if self._paused:
                outdata[:] = 0
                return

            try:
                chunk = self._sf.read(frames, dtype="float32")
            except Exception:
                self._finished = True
                outdata[:] = 0
                return

            if len(chunk) == 0:
                self._finished = True
                outdata[:] = 0
                return

            if chunk.ndim == 1:
                chunk = chunk.reshape(-1, 1)

            if self._volume != 1.0:
                chunk *= self._volume

            outdata[:len(chunk)] = chunk
            if len(chunk) < frames:
                outdata[len(chunk):] = 0
                self._finished = True

            self._current_frame += len(chunk)

    # ------------------------------------------------------------------
    # Control de posición y volumen
    # ------------------------------------------------------------------
    def seek(self, seconds: float):
        with self._lock:
            if self._sf is not None and self._samplerate > 0:
                frame = int(seconds * self._samplerate)
                frame = max(0, min(frame, self._total_frames - 1))
                self._sf.seek(frame)
                self._current_frame = frame
                self._finished = False

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))

    # ------------------------------------------------------------------
    # Propiedades de estado
    # ------------------------------------------------------------------
    @property
    def position(self) -> float:
        with self._lock:
            return self._current_frame / self._samplerate if self._samplerate else 0.0

    @property
    def duration(self) -> float:
        return self._total_frames / self._samplerate if self._samplerate else 0.0

    @property
    def is_playing(self) -> bool:
        return self._stream is not None and not self._paused and not self._finished

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def is_finished(self) -> bool:
        return self._finished

    @property
    def has_file(self) -> bool:
        return self._sf is not None
