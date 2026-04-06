"""
Editor Agent — Improves content based on Reviewer feedback and optional human notes.
Final stage of the Writer → Reviewer → Editor pipeline.
"""

import time
import google.generativeai as genai

from config.settings import settings


class EditorAgent:
    """Refines content using structured review feedback + human input."""

    def __init__(self, model_name: str | None = None, temperature: float | None = None):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name or settings.MODEL_NAME
        self.temperature = temperature if temperature is not None else settings.TEMPERATURE
        self.model = genai.GenerativeModel(self.model_name)

    def improve_content(
        self,
        content: str,
        review_feedback: dict,
        human_feedback: str | None = None,
    ) -> dict:
        """
        Apply *review_feedback* (and optional *human_feedback*) to improve *content*.
        Returns dict with 'improved' text and 'metadata'.
        """
        preview = content[:2000] + "..." if len(content) > 2000 else content
        improvements = review_feedback.get("improvements_needed", [])
        notes = review_feedback.get("overall_feedback", "")
        quality = review_feedback.get("quality_score", "N/A")

        prompt = (
            "You are an expert editor. Improve the content based on review feedback.\n\n"
            f"--- CONTENT ---\n{preview}\n\n"
            f"--- REVIEW FEEDBACK ---\n"
            f"Quality Score: {quality}/10\n"
            f"Improvements needed: {', '.join(improvements) if improvements else 'None'}\n"
            f"Reviewer notes: {notes}\n"
        )

        if human_feedback:
            prompt += f"\n--- HUMAN FEEDBACK ---\n{human_feedback}\n"

        prompt += "\nProvide the improved version addressing ALL feedback:"

        start = time.perf_counter()
        try:
            gen_cfg = genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=settings.MAX_OUTPUT_TOKENS,
            )
            response = self.model.generate_content(prompt, generation_config=gen_cfg)
            improved = response.text.strip()
            duration = time.perf_counter() - start

            return {
                "improved": improved,
                "metadata": {
                    "model": self.model_name,
                    "temperature": self.temperature,
                    "processing_time": duration,
                    "improvements_applied": improvements,
                    "had_human_feedback": human_feedback is not None,
                },
            }
        except Exception as e:
            raise RuntimeError(f"EditorAgent generation failed: {e}")
