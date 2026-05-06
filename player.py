"""Reproductor de audio con streaming en tiempo real"""

import threading

import soundfile as sf
import sounddevice as sd

from utils import suppress_stderr


class MusicPlayer:
    """Reproductor basado en soundfile y sounddevice"""

    def __init__(self):
        self._sf = None
        self._samplerate = 44100
        self._channels = 2
        self._current_frame = 0
        self._total_frames = 0
        self._volume = 0.7
        self._paused = False
        self._stop_flag = False
        self._stream = None
        self._lock = threading.Lock()
        self._finished = False
        self._file = None

    def load(self, filepath: str):
        """Carga un archivo en modo streaming"""
        self.stop()
        self._file = filepath
        try:
            with suppress_stderr():
                self._sf = sf.SoundFile(filepath, "r")
            self._samplerate = self._sf.samplerate
            self._channels = self._sf.channels
            self._total_frames = len(self._sf)
            self._current_frame = 0
            self._finished = False
        except Exception:
            self._sf = None
            self._file = None
            raise

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
                chunk = chunk * self._volume

            outdata[:len(chunk)] = chunk
            if len(chunk) < frames:
                outdata[len(chunk):] = 0
                self._finished = True

            self._current_frame += len(chunk)

    def play(self):
        if self._stream is not None:
            self.stop()
        if self._sf is None:
            return
        self._stop_flag = False
        self._paused = False
        self._finished = False
        self._stream = sd.OutputStream(
            samplerate=self._samplerate,
            channels=self._channels,
            dtype="float32",
            callback=self._callback,
            blocksize=2048
        )
        self._stream.start()

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def toggle_pause(self):
        self._paused = not self._paused

    def stop(self):
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

    def set_volume(self, vol: float):
        self._volume = max(0.0, min(1.0, vol))

    def get_pos(self) -> float:
        with self._lock:
            return self._current_frame / self._samplerate if self._samplerate > 0 else 0.0

    def get_duration(self) -> float:
        return self._total_frames / self._samplerate if self._samplerate > 0 else 0.0

    def seek(self, seconds: float):
        with self._lock:
            if self._sf is not None and self._samplerate > 0:
                frame = int(seconds * self._samplerate)
                frame = max(0, min(frame, self._total_frames - 1))
                self._sf.seek(frame)
                self._current_frame = frame
                self._finished = False

    def is_playing(self) -> bool:
        return self._stream is not None and not self._paused and not self._finished

    def is_paused(self) -> bool:
        return self._paused

    def is_finished(self) -> bool:
        return self._finished

    def has_file(self) -> bool:
        return self._file is not None