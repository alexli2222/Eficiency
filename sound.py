"""
sound.py — shared audio utility for Eficiency.

Public API:
    set_volume(v: float)  — set playback volume, 0.0 (silent) – 1.0 (full)
    get_volume() -> float — return current volume
    play_completed()      — play sounds/completed.mp3 non-blocking
"""
import os
import sys
import threading

_HERE      = os.path.dirname(os.path.abspath(__file__))
_COMPLETED = os.path.join(_HERE, "sounds", "completed.mp3")

_volume: float = 1.0


def set_volume(v: float) -> None:
    global _volume
    _volume = max(0.0, min(1.0, float(v)))


def get_volume() -> float:
    return _volume


def play_completed() -> None:
    """Play sounds/completed.mp3 at the current volume (non-blocking)."""
    v = _volume
    if v <= 0.0 or not os.path.isfile(_COMPLETED):
        return

    if sys.platform == "darwin":
        # afplay is built-in; Popen is already non-blocking
        _play_macos(_COMPLETED, v)
    elif sys.platform == "win32":
        # MCI's play-wait blocks, so run it in a daemon thread
        threading.Thread(
            target=_play_windows, args=(_COMPLETED, v), daemon=True
        ).start()
    else:
        # Generic fallback — requires pygame (optional)
        threading.Thread(
            target=_play_pygame, args=(_COMPLETED, v), daemon=True
        ).start()


# ── Backends ──────────────────────────────────────────────────────────────────

def _play_macos(path: str, volume: float) -> None:
    """afplay -v {volume} — built-in on macOS, supports MP3, truly non-blocking."""
    import subprocess
    try:
        subprocess.Popen(
            ["afplay", "-v", f"{volume:.4f}", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _play_windows(path: str, volume: float) -> None:
    """Windows MCI via ctypes — built-in, supports MP3.  Call from a thread."""
    try:
        import ctypes
        mci   = ctypes.windll.winmm.mciSendStringW
        alias = "eficiency_snd"
        path_w = os.path.normpath(path)
        mci(f'open "{path_w}" type mpegvideo alias {alias}', None, 0, 0)
        mci(f'setaudio {alias} volume to {int(volume * 1000)}',  None, 0, 0)
        mci(f'play {alias} wait',                                None, 0, 0)
        mci(f'close {alias}',                                    None, 0, 0)
    except Exception:
        pass


def _play_pygame(path: str, volume: float) -> None:
    """Fallback for Linux / other platforms if pygame is installed."""
    try:
        import time
        import pygame.mixer as mx  # type: ignore
        if not mx.get_init():
            mx.init()
        mx.music.load(path)
        mx.music.set_volume(volume)
        mx.music.play()
        while mx.music.get_busy():
            time.sleep(0.05)
    except Exception:
        pass
