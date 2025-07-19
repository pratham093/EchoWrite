
from gtts import gTTS
import pygame
import tempfile
import os
import time
import uuid

class SimpleVoiceInterface:
    """Simple voice interface that only does text-to-speech"""
    
    def __init__(self):
        pygame.mixer.init()
        self.temp_files = []
        
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'echowrite_voice')
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def speak(self, text: str):
        """Convert text to speech"""
        temp_file_path = None
        try:
            
            filename = f"echowrite_tts_{uuid.uuid4().hex[:8]}.mp3"
            temp_file_path = os.path.join(self.temp_dir, filename)
            
            print(f"Creating TTS file at: {temp_file_path}")
            
            
            tts = gTTS(text=text, lang='en')
            tts.save(temp_file_path)
            
        
            if not os.path.exists(temp_file_path):
                raise FileNotFoundError(f"TTS file not created: {temp_file_path}")
            
            print(f"File size: {os.path.getsize(temp_file_path)} bytes")
            
            
            self.temp_files.append(temp_file_path)
            
            
            pygame.mixer.music.load(temp_file_path)
            pygame.mixer.music.play()
            
            
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
        
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            
        
            time.sleep(0.1)
            
        
            try:
                os.remove(temp_file_path)
                self.temp_files.remove(temp_file_path)
            except:
                pass  
            
            print("✅ Speech completed successfully")
            
        except Exception as e:
            print(f"TTS Error: {e}")
        
            print(f"[VOICE]: {text}")
            
            
            self._try_alternative_tts(text)
    
    def _try_alternative_tts(self, text: str):
        """Try alternative TTS using pyttsx3"""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            print("✅ Used pyttsx3 for speech")
        except:
            try:
                import win32com.client
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                speaker.Speak(text)
                print("✅ Used Windows SAPI for speech")
            except:
                print("❌ No working TTS engine found")
    
    def cleanup(self):
        """Clean up resources"""
        pygame.mixer.quit()
        
        
        for f in self.temp_files[:]:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"Cleaned up: {f}")
            except:
                pass
        
    
        try:
            if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
                os.rmdir(self.temp_dir)
        except:
            pass


if __name__ == "__main__":
    print("Testing Simple Voice Interface...\n")
    
    voice = SimpleVoiceInterface()
    
    
    print("Test 1: Basic speech")
    voice.speak("Hello, this is a test of the simple voice interface.")
    
    print("\nTest 2: Longer text")
    voice.speak("The EchoWrite system is now ready. You can process content using AI agents.")
    
    voice.cleanup()
    print("\nTest completed!")