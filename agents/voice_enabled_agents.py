"""
Voice-Enabled Agent Wrappers — Thin decorators around the core agents
that announce progress and results via the VoiceInterface.
"""

from agents.writer import WriterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.editor_agent import EditorAgent
from agents.voice_interface import VoiceInterface


class VoiceEnabledWriterAgent(WriterAgent):
    def __init__(self, voice_enabled: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.voice = VoiceInterface() if voice_enabled else None

    def rewrite_content(self, content: str, style: str = "engaging") -> dict:
        if self.voice:
            self.voice.speak(f"Starting rewrite in {style} style", wait=False)
        result = super().rewrite_content(content, style)
        if self.voice:
            wc = len(result["rewritten"].split())
            self.voice.speak(f"Rewrite complete — {wc} words of {style} content.")
        return result


class VoiceEnabledReviewerAgent(ReviewerAgent):
    def __init__(self, voice_enabled: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.voice = VoiceInterface() if voice_enabled else None

    def review_content(self, original: str, rewritten: str) -> dict:
        if self.voice:
            self.voice.speak("Analysing content quality", wait=False)
        result = super().review_content(original, rewritten)
        if self.voice:
            qs = result.get("quality_score", 0)
            self.voice.speak(f"Review complete. Quality score: {qs} out of 10.")
            if qs >= 8:
                self.voice.speak("Excellent — content is ready.")
            elif qs >= 6:
                self.voice.speak("Good, but could use improvements.")
            else:
                self.voice.speak("Needs significant revision.")
        return result


class VoiceEnabledEditorAgent(EditorAgent):
    def __init__(self, voice_enabled: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.voice = VoiceInterface() if voice_enabled else None

    def improve_content(self, content: str, review_feedback: dict, human_feedback: str = None) -> dict:
        if self.voice:
            n = len(review_feedback.get("improvements_needed", []))
            self.voice.speak(f"Making {n} improvements" if n else "Polishing content", wait=False)
        result = super().improve_content(content, review_feedback, human_feedback)
        if self.voice:
            self.voice.speak("Editing complete.")
        return result
