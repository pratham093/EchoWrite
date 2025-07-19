import time
import google.generativeai as genai
from config.settings import settings

class WriterAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash-exp", temperature: float = 0.7):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name
        self.temperature = temperature
        self.model = genai.GenerativeModel(self.model_name)

    def rewrite_content(self, content: str, style: str = "engaging") -> dict:
        # Prepare content preview to fit token limits
        preview = content if len(content) <= 3000 else content[:3000] + "..."
        prompt = (
            f"You are an expert content writer. Rewrite the following content to be more {style}. "
            "Keep the core information but improve readability and engagement."
            f"\n\nOriginal content:\n{preview}\n\nRewritten version:" 
        )

        start_time = time.perf_counter()
        try:
            # Use generation_config for temperature
            generation_config = genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=8192,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            rewritten = response.text.strip()
            duration = time.perf_counter() - start_time
            
            return {
                "rewritten": rewritten,
                "metadata": {
                    "model": self.model_name,
                    "temperature": self.temperature,
                    "processing_time": duration
                }
            }
        except Exception as e:
            raise RuntimeError(f"AI generation failed: {e}")