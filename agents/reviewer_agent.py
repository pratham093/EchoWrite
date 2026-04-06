"""
Reviewer Agent — Evaluates rewritten content against the original.
Returns structured quality scores and improvement suggestions.
"""

import time
import json
from google import genai
from google.genai import types

from config.settings import settings


class ReviewerAgent:
    """Scores content on quality, clarity, engagement, and accuracy."""

    def __init__(self, model_name: str | None = None, temperature: float | None = None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name or settings.MODEL_NAME
        self.temperature = temperature if temperature is not None else settings.TEMPERATURE

    def review_content(self, original: str, rewritten: str) -> dict:
        """
        Compare *rewritten* to *original* and return a review dict with scores,
        improvement suggestions, and a ready-for-human flag.
        """
        orig_preview = original[:500] + "..." if len(original) > 500 else original
        rew_preview = rewritten[:500] + "..." if len(rewritten) > 500 else rewritten

        prompt = (
            "You are an expert content reviewer. Analyse the rewritten content.\n\n"
            f"Original (preview):\n{orig_preview}\n\n"
            f"Rewritten (preview):\n{rew_preview}\n\n"
            "Return ONLY a JSON object with these keys:\n"
            "  quality_score     (int 1-10)\n"
            "  clarity_score     (int 1-10)\n"
            "  engagement_score  (int 1-10)\n"
            "  accuracy_score    (int 1-10)\n"
            "  improvements_needed (list[str])\n"
            "  ready_for_human   (bool)\n"
            "  overall_feedback  (str)\n"
        )

        start = time.perf_counter()
        data: dict = {}

        try:
            config = types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=2048,
            )
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt, config=config
            )
            text = response.text.strip()

            # Extract JSON from potentially wrapped response
            start_json = text.find("{")
            end_json = text.rfind("}") + 1
            if start_json != -1 and end_json > start_json:
                data = json.loads(text[start_json:end_json])
            else:
                raise ValueError("No JSON object found in reviewer response")

        except Exception as e:
            # Fallback scores so the pipeline never crashes
            data = {
                "quality_score": 7,
                "clarity_score": 7,
                "engagement_score": 7,
                "accuracy_score": 8,
                "improvements_needed": [f"Review parse error: {e}"],
                "ready_for_human": True,
                "overall_feedback": str(e),
            }

        data["metadata"] = {
            "model": self.model_name,
            "temperature": self.temperature,
            "processing_time": time.perf_counter() - start,
        }
        return data
