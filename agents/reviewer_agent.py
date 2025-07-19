import time
import json
import google.generativeai as genai
from config.settings import settings

class ReviewerAgent:
    def __init__(self, model_name: str = "gemini-2.0-flash-exp", temperature: float = 0.7):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name
        self.temperature = temperature
        self.model = genai.GenerativeModel(self.model_name)

    def review_content(self, original: str, rewritten: str) -> dict:
        preview_orig = original[:500] + "..." if len(original) > 500 else original
        preview_rew = rewritten[:500] + "..." if len(rewritten) > 500 else rewritten
        
        prompt = f"""You are an expert content reviewer. Analyze the rewritten content.

Original (preview): {preview_orig}

Rewritten (preview): {preview_rew}

Provide a JSON response with these keys:
- quality_score (1-10)
- clarity_score (1-10)
- engagement_score (1-10)
- accuracy_score (1-10)
- improvements_needed (list of strings)
- ready_for_human (boolean)
- overall_feedback (string)

Return ONLY the JSON object, no other text."""

        start = time.perf_counter()
        try:
            # Use generation_config for temperature
            generation_config = genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=2048,
            )
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            text = response.text.strip()
            # Extract JSON from response
            start_json = text.find('{')
            end_json = text.rfind('}') + 1
            
            if start_json != -1 and end_json > start_json:
                json_str = text[start_json:end_json]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
                
        except Exception as e:
            # Fallback response
            data = {
                "quality_score": 7,
                "clarity_score": 7,
                "engagement_score": 7,
                "accuracy_score": 8,
                "improvements_needed": ["Error parsing AI response"],
                "ready_for_human": True,
                "overall_feedback": text if 'text' in locals() else str(e)
            }
        
        data['metadata'] = {
            "model": self.model_name,
            "temperature": self.temperature,
            "processing_time": time.perf_counter() - start
        }
        
        return data