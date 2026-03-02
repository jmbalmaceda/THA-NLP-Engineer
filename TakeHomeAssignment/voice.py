"""Voice I/O providers for STT (Speech-to-Text) and TTS (Text-to-Speech).

Supported STT providers:
  - whisper   (default) — local, faster-whisper + sounddevice (Python 3.13 compatible)
  - google              — cloud, SpeechRecognition + Google Web Speech API (no key)

Supported TTS providers:
  - say       (default) — macOS built-in `say` command, zero deps
  - pyttsx3             — offline, cross-platform, pyttsx3
  - edge                — Microsoft Edge TTS, high quality, requires internet

Configuration (env vars or get_*_provider(name=...)):
  STT_PROVIDER       = whisper | google
  TTS_PROVIDER       = say | pyttsx3 | edge
  WHISPER_MODEL      = tiny | base (default) | small | medium | large
  SAY_VOICE          = macOS voice name, e.g. Samantha (leave blank for system default)
  SAY_RATE           = words per minute, e.g. 180 (leave blank for system default)
  EDGE_TTS_VOICE     = BCP-47 voice name, default en-US-JennyNeural
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Protocol, runtime_checkable


# ─── Protocols ────────────────────────────────────────────────────────────────

@runtime_checkable
class STTProvider(Protocol):
    def listen(self) -> str:
        """Record audio from the microphone and return the transcribed text."""
        ...


@runtime_checkable
class TTSProvider(Protocol):
    def speak(self, text: str) -> None:
        """Synthesise speech from *text* and play it through the speakers."""
        ...


# ─── STT: Whisper (local) ─────────────────────────────────────────────────────

class WhisperSTT:
    """Local STT using faster-whisper + sounddevice for audio capture.

    Uses CTranslate2 under the hood — no numba dependency, works on Python 3.13.

    Requires:
        pip install faster-whisper sounddevice soundfile
    """

    def __init__(self, model_size: str = "base") -> None:
        try:
            from faster_whisper import WhisperModel  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "faster-whisper is not installed. "
                "Run: pip install faster-whisper sounddevice soundfile"
            ) from exc
        print(f"[WhisperSTT] Loading model '{model_size}'…")
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def listen(self) -> str:
        import soundfile as sf  # noqa: PLC0415

        print("Recording… press Enter to stop.")
        audio = _record_until_enter()
        print("Transcribing…")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio, _SAMPLE_RATE)
            tmp_path = tmp.name

        try:
            segments, _ = self._model.transcribe(tmp_path)
            text = " ".join(seg.text for seg in segments).strip()
        finally:
            os.unlink(tmp_path)

        print(f"You said: {text}")
        return text


# ─── STT: Google (cloud) ──────────────────────────────────────────────────────

class GoogleSTT:
    """Cloud STT via Google Web Speech API — no API key required for basic use.

    Uses sounddevice for audio capture (no PyAudio / portaudio needed).

    Requires:
        pip install SpeechRecognition sounddevice soundfile
    """

    def listen(self) -> str:
        try:
            import speech_recognition as sr  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "SpeechRecognition is not installed. "
                "Run: pip install SpeechRecognition sounddevice soundfile"
            ) from exc
        import soundfile as sf  # noqa: PLC0415

        print("Recording… press Enter to stop.")
        audio = _record_until_enter()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            sf.write(tmp.name, audio, _SAMPLE_RATE)
            tmp_path = tmp.name

        print("Transcribing…")
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
            except sr.UnknownValueError:
                print("(no speech detected)")
                return ""
        finally:
            os.unlink(tmp_path)

        print(f"You said: {text}")
        return text


# ─── TTS: macOS say ───────────────────────────────────────────────────────────

class MacSayTTS:
    """TTS using the macOS built-in `say` command (no extra dependencies).

    Args:
        voice: macOS voice name, e.g. "Samantha", "Alex", "Karen".
               Pass None to use the system default.
        rate:  Speaking rate in words per minute (e.g. 180).
               Pass None to use the system default.
    """

    def __init__(self, voice: str | None = None, rate: int | None = None) -> None:
        self._voice = voice
        self._rate = rate

    def speak(self, text: str) -> None:
        cmd = ["say"]
        if self._voice:
            cmd += ["-v", self._voice]
        if self._rate:
            cmd += ["-r", str(self._rate)]
        cmd.append(text)
        subprocess.run(cmd, check=True)


# ─── TTS: pyttsx3 (cross-platform, offline) ──────────────────────────────────

class Pyttsx3TTS:
    """Offline, cross-platform TTS using pyttsx3.

    Requires:
        pip install pyttsx3
    """

    def __init__(self, rate: int = 175) -> None:
        try:
            import pyttsx3  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "pyttsx3 is not installed. Run: pip install pyttsx3"
            ) from exc
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", rate)

    def speak(self, text: str) -> None:
        self._engine.say(text)
        self._engine.runAndWait()


# ─── TTS: Microsoft Edge TTS (cloud, high quality) ───────────────────────────

class EdgeTTS:
    """High-quality cloud TTS via Microsoft Edge (free, requires internet).

    Requires:
        pip install edge-tts

    On macOS the generated MP3 is played with `afplay`.
    On Linux, install and use `mpg123` (or set EDGE_TTS_PLAYER env var).
    """

    def __init__(self, voice: str = "en-US-JennyNeural") -> None:
        try:
            import edge_tts  # noqa: PLC0415, F401
        except ImportError as exc:
            raise ImportError(
                "edge-tts is not installed. Run: pip install edge-tts"
            ) from exc
        self._voice = voice

    def speak(self, text: str) -> None:
        import asyncio  # noqa: PLC0415
        import edge_tts  # noqa: PLC0415

        async def _synthesize(path: str) -> None:
            communicate = edge_tts.Communicate(text, self._voice)
            await communicate.save(path)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            asyncio.run(_synthesize(tmp_path))
            player = os.getenv("EDGE_TTS_PLAYER", "afplay")
            subprocess.run([player, tmp_path], check=True)
        finally:
            os.unlink(tmp_path)


# ─── Audio recording helper ───────────────────────────────────────────────────

_SAMPLE_RATE = 16_000  # Hz — Whisper expects 16 kHz


def _record_until_enter():
    """Record from the default microphone until the user presses Enter.

    Uses sd.InputStream with a callback so the microphone stays open
    continuously (no blinking indicator) until Enter is pressed.

    Returns a float32 numpy array at *_SAMPLE_RATE* Hz.
    """
    import numpy as np        # noqa: PLC0415
    import sounddevice as sd  # noqa: PLC0415

    chunks: list = []

    def _callback(indata, frames, time, status):
        chunks.append(indata.copy())

    with sd.InputStream(samplerate=_SAMPLE_RATE, channels=1, dtype="float32", callback=_callback):
        try:
            input()  # blocks until Enter; mic stays open the whole time
        except (EOFError, KeyboardInterrupt):
            pass

    if not chunks:
        return np.zeros((0, 1), dtype="float32")
    return np.concatenate(chunks, axis=0)


# ─── Provider registries & factories ─────────────────────────────────────────

_STT_REGISTRY: dict[str, type] = {
    "whisper": WhisperSTT,
    "google":  GoogleSTT,
}

_TTS_REGISTRY: dict[str, type] = {
    "say":     MacSayTTS,
    "pyttsx3": Pyttsx3TTS,
    "edge":    EdgeTTS,
}


def get_stt_provider(name: str | None = None) -> STTProvider:
    """Return an STT provider instance.

    *name* overrides the ``STT_PROVIDER`` environment variable (default: ``whisper``).
    """
    name = name or os.getenv("STT_PROVIDER", "whisper")
    cls = _STT_REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown STT provider: {name!r}. "
            f"Available: {list(_STT_REGISTRY)}"
        )
    if cls is WhisperSTT:
        model_size = os.getenv("WHISPER_MODEL", "base")
        return cls(model_size=model_size)
    return cls()


def get_tts_provider(name: str | None = None) -> TTSProvider:
    """Return a TTS provider instance.

    *name* overrides the ``TTS_PROVIDER`` environment variable (default: ``say``).
    """
    name = name or os.getenv("TTS_PROVIDER", "say")
    cls = _TTS_REGISTRY.get(name)
    if cls is None:
        raise ValueError(
            f"Unknown TTS provider: {name!r}. "
            f"Available: {list(_TTS_REGISTRY)}"
        )
    if cls is MacSayTTS:
        voice = os.getenv("SAY_VOICE") or None
        raw_rate = os.getenv("SAY_RATE", "")
        rate = int(raw_rate) if raw_rate.strip() else None
        return cls(voice=voice, rate=rate)
    if cls is EdgeTTS:
        voice = os.getenv("EDGE_TTS_VOICE", "en-US-JennyNeural")
        return cls(voice=voice)
    return cls()
