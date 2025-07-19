import time
import google.generativeai as genai
from config.settings import settings

class EditorAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash-exp", temperature: float = 0.7):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name
        self.temperature = temperature
        self.model = genai.GenerativeModel(self.model_name)

    def improve_content(self, content: str, review_feedback: dict, human_feedback: str = None) -> dict:
        preview = content[:2000] + "..." if len(content) > 2000 else content
        improvements = review_feedback.get('improvements_needed', [])
        notes = review_feedback.get('overall_feedback', '')
        quality = review_feedback.get('quality_score', 'N/A')

        prompt = f"""You are an expert editor. Improve the content based on the following feedback.

Content:
{preview}

Review Feedback:
- Quality Score: {quality}/10
- Improvements needed: {', '.join(improvements) if improvements else 'None'}
- Reviewer notes: {notes}"""

        if human_feedback:
            prompt += f"\n\nHuman feedback: {human_feedback}"
            
        prompt += "\n\nProvide the improved version addressing all feedback:"

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
            
            improved = response.text.strip()
            duration = time.perf_counter() - start_time
            
            return {
                "improved": improved,
                "metadata": {
                    "model": self.model_name,
                    "temperature": self.temperature,
                    "processing_time": duration
                }
            }
        except Exception as e:
            raise RuntimeError(f"AI editing failed: {e}")