# agents/voice_enabled_agents.py - Fixed version
from agents.writer import WriterAgent
from agents.reviewer_agent import ReviewerAgent
from agents.editor_agent import EditorAgent
from agents.voice_interface import VoiceInterface
from typing import Optional

class VoiceEnabledWriterAgent(WriterAgent):
    def __init__(self, voice_enabled: bool = True):
        super().__init__()
        self.voice = VoiceInterface() if voice_enabled else None
    
    def rewrite_content(self, content: str, style: str = "engaging") -> dict:
        if self.voice:
            self.voice.speak(f"Starting to rewrite content in {style} style", wait=False)
        
        result = super().rewrite_content(content, style)
        
        if self.voice:
            word_count = len(result['rewritten'].split())
            self.voice.speak(f"Rewriting complete. Created {word_count} words of {style} content.")
        
        return result

class VoiceEnabledReviewerAgent(ReviewerAgent):
    def __init__(self, voice_enabled: bool = True):
        super().__init__()
        self.voice = VoiceInterface() if voice_enabled else None
    
    def review_content(self, original: str, rewritten: str) -> dict:
        if self.voice:
            self.voice.speak("Analyzing content quality", wait=False)
        
        result = super().review_content(original, rewritten)
        
        if self.voice:
            quality_score = result.get('quality_score', 0)
            self.voice.speak(f"Review complete. Quality score is {quality_score} out of 10.")
            
            if quality_score >= 8:
                self.voice.speak("Excellent work! This content is ready.")
            elif quality_score >= 6:
                self.voice.speak("Good content, but could use some improvements.")
            else:
                self.voice.speak("This content needs significant revision.")
        
        return result

class VoiceEnabledEditorAgent(EditorAgent):
    def __init__(self, voice_enabled: bool = True):
        super().__init__()
        self.voice = VoiceInterface() if voice_enabled else None
    
    def improve_content(self, content: str, review_feedback: dict, human_feedback: str = None) -> dict:
        if self.voice:
            improvements = review_feedback.get('improvements_needed', [])
            if improvements:
                self.voice.speak(f"Making {len(improvements)} improvements to the content", wait=False)
            else:
                self.voice.speak("Polishing the content", wait=False)
        
        result = super().improve_content(content, review_feedback, human_feedback)
        
        if self.voice:
            self.voice.speak("Editing complete. Content has been improved.")
        
        return result