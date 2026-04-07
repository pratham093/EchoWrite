"""
Voice Interface — Speech recognition + text-to-speech with multiple backend fallbacks.
Parses natural-language voice commands into structured intents for the agentic pipeline.
"""

import os
import re
import tempfile
import threading
import queue
import time
import uuid
from typing import Optional, Dict

from config.settings import settings

# ---------- graceful optional imports ----------
SPEECH_RECOGNITION_AVAILABLE = False
TTS_AVAILABLE = False
PYGAME_AVAILABLE = False
PYTTSX3_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    sr = None

try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    pass

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    pass

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass


class VoiceInterface:
    """Bidirectional voice I/O for agentic communication."""

    def __init__(self, language: str | None = None):
        self.language = language or settings.VOICE_LANGUAGE
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception:
                pass

        self.is_speaking = False
        self.voice_queue: queue.Queue[str | None] = queue.Queue()
        self.temp_files: list[str] = []

        self.temp_dir = os.path.join(tempfile.gettempdir(), "echowrite_voice")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.pyttsx3_engine = None
        if PYTTSX3_AVAILABLE:
            try:
                self.pyttsx3_engine = pyttsx3.init()
            except Exception:
                pass

        # Background voice-queue thread
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Speech-to-text
    # ------------------------------------------------------------------
    def listen_for_command(self, timeout: int | None = None) -> Optional[str]:
        """Listen via microphone → text (Google STT)."""
        timeout = timeout or settings.VOICE_TIMEOUT
        if not self.recognizer:
            print("❌ Speech recognition not available")
            return None
        try:
            with sr.Microphone() as source:
                print("🎤 Listening… (speak now)")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout)
            text = self.recognizer.recognize_google(audio, language=self.language)
            print(f"📝 Heard: {text}")
            return text
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"❌ Mic error: {e}")
            return None

    # ------------------------------------------------------------------
    # Text-to-speech
    # ------------------------------------------------------------------
    def speak(self, text: str, wait: bool = True):
        if wait:
            self._speak_now(text)
        else:
            self.voice_queue.put(text)

    def _speak_now(self, text: str):
        self.is_speaking = True
        success = False

        if TTS_AVAILABLE and PYGAME_AVAILABLE:
            success = self._speak_gtts(text)
        if not success and self.pyttsx3_engine:
            success = self._speak_pyttsx3(text)
        if not success:
            success = self._speak_sapi(text)
        if not success:
            print(f"💬 [Voice]: {text}")

        self.is_speaking = False

    def _speak_gtts(self, text: str) -> bool:
        try:
            path = os.path.join(self.temp_dir, f"tts_{uuid.uuid4().hex[:8]}.mp3")
            gTTS(text=text, lang=self.language).save(path)
            self.temp_files.append(path)
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            time.sleep(0.1)
            self._remove(path)
            return True
        except Exception:
            return False

    def _speak_pyttsx3(self, text: str) -> bool:
        try:
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()
            return True
        except Exception:
            return False

    @staticmethod
    def _speak_sapi(text: str) -> bool:
        try:
            import win32com.client
            win32com.client.Dispatch("SAPI.SpVoice").Speak(text)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Voice-command parsing
    # ------------------------------------------------------------------
    def parse_voice_command(self, command: str) -> Dict:
        low = command.lower()

        if any(w in low for w in ("process", "analyze", "rewrite")):
            words = command.split()
            urls = [w for w in words if w.startswith(("http://", "https://", "www."))]
            return {"intent": "process_url", "url": urls[0] if urls else None, "style": self._extract_style(low)}

        if any(w in low for w in ("rate", "rating", "score")):
            nums = re.findall(r"\d+", command)
            return {"intent": "provide_feedback", "rating": int(nums[0]) if nums else None, "feedback": command}

        if any(w in low for w in ("search", "find", "look for")):
            q = low
            for t in ("search", "find", "look for", "for"):
                q = q.replace(t, "")
            return {"intent": "search", "query": q.strip()}

        if any(w in low for w in ("status", "progress")):
            return {"intent": "get_status"}

        if any(w in low for w in ("help", "commands")):
            return {"intent": "help"}

        return {"intent": "unknown", "command": command}

    @staticmethod
    def _extract_style(text: str) -> str:
        mapping = {
            "professional": ("professional", "formal", "business"),
            "casual": ("casual", "informal", "relaxed"),
            "engaging": ("engaging", "interesting", "captivating"),
            "academic": ("academic", "scholarly", "research"),
            "creative": ("creative", "artistic", "imaginative"),
        }
        for style, keywords in mapping.items():
            if any(k in text for k in keywords):
                return style
        return "engaging"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _process_queue(self):
        while True:
            try:
                text = self.voice_queue.get(timeout=1)
                if text is None:
                    break
                self._speak_now(text)
            except queue.Empty:
                continue

    def _remove(self, path: str):
        try:
            os.remove(path)
            self.temp_files.remove(path)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def shutdown(self):
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass
        self.voice_queue.put(None)
        try:
            self._thread.join(timeout=2)
        except Exception:
            pass
        for f in list(self.temp_files):
            self._remove(f)
