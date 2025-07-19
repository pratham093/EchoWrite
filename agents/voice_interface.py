# Save as agents/voice_interface.py

import os
import io
import tempfile
import threading
import queue
import time
import uuid
from typing import Optional, Dict

# Handle imports gracefully
SPEECH_RECOGNITION_AVAILABLE = False
TTS_AVAILABLE = False
PYGAME_AVAILABLE = False

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    print("Warning: speech_recognition not available")
    sr = None

try:
    from gtts import gTTS
    TTS_AVAILABLE = True
except ImportError:
    print("Warning: gtts not available")
    
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    print("Warning: pygame not available")

# Try alternative TTS engines
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

class VoiceInterface:
    """Voice interface for agentic communication"""
    
    def __init__(self, language='en'):
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        self.language = language
        
        if PYGAME_AVAILABLE:
            pygame.mixer.init()
        
        self.is_speaking = False
        self.voice_queue = queue.Queue()
        self.temp_files = []
        
        # Create temp directory
        self.temp_dir = os.path.join(tempfile.gettempdir(), 'echowrite_voice')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize alternative TTS
        self.pyttsx3_engine = None
        if PYTTSX3_AVAILABLE:
            try:
                self.pyttsx3_engine = pyttsx3.init()
            except:
                pass
        
        # Start voice processing thread
        self.voice_thread = threading.Thread(target=self._process_voice_queue, daemon=True)
        self.voice_thread.start()
    
    def listen_for_command(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice input and convert to text"""
        if not SPEECH_RECOGNITION_AVAILABLE or not self.recognizer:
            print("❌ Speech recognition not available")
            return None
            
        try:
            with sr.Microphone() as source:
                print("🎤 Listening... (speak now)")
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Listen with timeout
                audio = self.recognizer.listen(source, timeout=timeout)
                
            # Convert to text
            print("🔄 Processing speech...")
            text = self.recognizer.recognize_google(audio, language=self.language)
            print(f"📝 Heard: {text}")
            return text
            
        except sr.WaitTimeoutError:
            print("⏱️ No speech detected (timeout)")
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"❌ Speech recognition error: {e}")
            return None
        except Exception as e:
            print(f"❌ Microphone error: {e}")
            print("Make sure a microphone is connected and permissions are granted")
            return None
    
    def speak(self, text: str, wait: bool = True):
        """Convert text to speech and play it"""
        if wait:
            self._speak_now(text)
        else:
            # Add to queue for background processing
            self.voice_queue.put(text)
    
    def _speak_now(self, text: str):
        """Immediately speak the given text"""
        self.is_speaking = True
        
        # Try different TTS methods in order
        success = False
        
        # Method 1: gTTS + pygame
        if TTS_AVAILABLE and PYGAME_AVAILABLE:
            success = self._speak_with_gtts(text)
        
        # Method 2: pyttsx3
        if not success and PYTTSX3_AVAILABLE and self.pyttsx3_engine:
            success = self._speak_with_pyttsx3(text)
        
        # Method 3: Windows SAPI
        if not success:
            success = self._speak_with_sapi(text)
        
        # Method 4: Console fallback
        if not success:
            print(f"💬 [Voice output]: {text}")
        
        self.is_speaking = False
    
    def _speak_with_gtts(self, text: str) -> bool:
        """Speak using gTTS and pygame"""
        temp_file_path = None
        try:
            # Generate unique filename
            filename = f"echowrite_tts_{uuid.uuid4().hex[:8]}.mp3"
            temp_file_path = os.path.join(self.temp_dir, filename)
            
            # Generate speech
            tts = gTTS(text=text, lang=self.language)
            tts.save(temp_file_path)
            
            # Verify file exists
            if not os.path.exists(temp_file_path):
                return False
            
            self.temp_files.append(temp_file_path)
            
            # Play audio
            pygame.mixer.music.load(temp_file_path)
            pygame.mixer.music.play()
            
            # Wait for playback
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Cleanup
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
            time.sleep(0.1)
            
            # Try to remove file
            try:
                os.remove(temp_file_path)
                self.temp_files.remove(temp_file_path)
            except:
                pass
            
            return True
            
        except Exception as e:
            print(f"gTTS error: {e}")
            return False
    
    def _speak_with_pyttsx3(self, text: str) -> bool:
        """Speak using pyttsx3"""
        try:
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()
            return True
        except Exception as e:
            print(f"pyttsx3 error: {e}")
            return False
    
    def _speak_with_sapi(self, text: str) -> bool:
        """Speak using Windows SAPI"""
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
            return True
        except:
            return False
    
    def _process_voice_queue(self):
        """Process voice queue in background"""
        while True:
            try:
                text = self.voice_queue.get(timeout=1)
                if text is None:  # Shutdown signal
                    break
                self._speak_now(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Queue processing error: {e}")
    
    def parse_voice_command(self, command: str) -> Dict:
        """Parse voice command to extract intent and parameters"""
        command_lower = command.lower()
        
        # URL processing commands
        if any(word in command_lower for word in ['process', 'analyze', 'rewrite']):
            # Extract URL if present
            words = command.split()
            urls = [w for w in words if w.startswith(('http://', 'https://', 'www.'))]
            
            # Also check for common domains
            domain_words = [w for w in words if any(domain in w for domain in ['.com', '.org', '.net', '.edu'])]
            if not urls and domain_words:
                urls = domain_words
            
            return {
                'intent': 'process_url',
                'url': urls[0] if urls else None,
                'style': self._extract_style(command_lower)
            }
        
        # Feedback commands
        elif any(word in command_lower for word in ['rate', 'rating', 'score']):
            # Extract rating
            import re
            numbers = re.findall(r'\d+', command)
            rating = int(numbers[0]) if numbers else None
            
            return {
                'intent': 'provide_feedback',
                'rating': rating,
                'feedback': command
            }
        
        # Search commands
        elif any(word in command_lower for word in ['search', 'find', 'look for']):
            # Extract search query
            search_terms = command_lower
            for term in ['search', 'find', 'look for', 'for']:
                search_terms = search_terms.replace(term, '')
            search_terms = search_terms.strip()
            
            return {
                'intent': 'search',
                'query': search_terms
            }
        
        # Status commands
        elif any(word in command_lower for word in ['status', 'progress', 'how are you']):
            return {'intent': 'get_status'}
        
        # Help commands
        elif any(word in command_lower for word in ['help', 'what can you do', 'commands']):
            return {'intent': 'help'}
        
        else:
            return {'intent': 'unknown', 'command': command}
    
    def _extract_style(self, text: str) -> str:
        """Extract writing style from voice command"""
        styles = {
            'professional': ['professional', 'formal', 'business'],
            'casual': ['casual', 'informal', 'relaxed'],
            'engaging': ['engaging', 'interesting', 'captivating'],
            'academic': ['academic', 'scholarly', 'research'],
            'creative': ['creative', 'artistic', 'imaginative']
        }
        
        for style, keywords in styles.items():
            if any(keyword in text for keyword in keywords):
                return style
        
        return 'engaging'  # default
    
    def get_voice_help(self) -> str:
        """Get help text for voice commands"""
        return """
        Available voice commands:
        - "Process [URL] in [style] style"
        - "Search for [keywords]"
        - "Rate this 8 out of 10"
        - "What's the status?"
        - "Help" or "What can you do?"
        """
    
    def cleanup_temp_files(self):
        """Clean up any remaining temporary files"""
        for temp_file in self.temp_files[:]:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                self.temp_files.remove(temp_file)
            except:
                pass
    
    def shutdown(self):
        """Shutdown voice interface"""
        # Stop music if playing
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
                pygame.mixer.quit()
            except:
                pass
        
        # Signal thread to stop
        self.voice_queue.put(None)
        try:
            self.voice_thread.join(timeout=2)
        except:
            pass
        
        # Clean up temp files
        self.cleanup_temp_files()
        
        # Clean up temp directory
        try:
            if os.path.exists(self.temp_dir) and not os.listdir(self.temp_dir):
                os.rmdir(self.temp_dir)
        except:
            pass

# Simple test function
def test_voice_simple():
    """Simple test of voice functionality"""
    print("Testing EchoWrite Voice Interface\n")
    
    voice = VoiceInterface()
    
    try:
        # Test speech output
        print("Testing text-to-speech...")
        voice.speak("Hello! This is EchoWrite voice interface.")
        
        # Test speech input (if available)
        if SPEECH_RECOGNITION_AVAILABLE:
            print("\nTesting speech recognition...")
            voice.speak("Please say something.")
            
            text = voice.listen_for_command(timeout=5)
            
            if text:
                voice.speak(f"I heard: {text}")
                parsed = voice.parse_voice_command(text)
                print(f"Parsed as: {parsed}")
            else:
                voice.speak("I didn't hear anything.")
        else:
            print("Speech recognition not available")
        
        voice.speak("Test complete!")
        
    except Exception as e:
        print(f"Error during test: {e}")
    
    finally:
        # Always cleanup
        voice.shutdown()
        print("\nVoice interface shut down properly.")

if __name__ == "__main__":
    test_voice_simple()