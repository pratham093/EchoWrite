"""
Writer Agent — Rewrites raw scraped content into a target style using Gemini.
Part of the multi-agent Writer → Reviewer → Editor pipeline.
"""

import time
from google import genai
from google.genai import types

from config.settings import settings


class WriterAgent:
    """Generates rewritten content from raw source material."""

    STYLE_PROMPTS = {
        "engaging": "Make it vivid, compelling, and easy to read with strong hooks.",
        "professional": "Use a polished, authoritative tone suitable for business audiences.",
        "casual": "Write in a friendly, conversational, approachable tone.",
        "academic": "Use formal, well-structured prose with precise terminology.",
        "creative": "Be expressive and literary — use metaphor, imagery, and narrative flair.",
    }

    def __init__(self, model_name: str | None = None, temperature: float | None = None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = model_name or settings.MODEL_NAME
        self.temperature = temperature if temperature is not None else settings.TEMPERATURE

    def rewrite_content(self, content: str, style: str = "engaging") -> dict:
        """
        Rewrite *content* in the requested *style*.
        Returns dict with 'rewritten' text and 'metadata'.
        """
        preview = content[:3000] + "..." if len(content) > 3000 else content
        style_guidance = self.STYLE_PROMPTS.get(style, self.STYLE_PROMPTS["engaging"])

        prompt = (
            f"You are an expert content writer.\n"
            f"Style goal: {style} — {style_guidance}\n\n"
            f"Rewrite the following content while preserving all core information.\n"
            f"Improve readability, structure, and engagement.\n\n"
            f"--- ORIGINAL CONTENT ---\n{preview}\n\n"
            f"--- REWRITTEN VERSION ---"
        )

        start = time.perf_counter()
        try:
            config = types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=settings.MAX_OUTPUT_TOKENS,
            )
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt, config=config
            )
            rewritten = response.text.strip()
            duration = time.perf_counter() - start

            return {
                "rewritten": rewritten,
                "metadata": {
                    "model": self.model_name,
                    "style": style,
                    "temperature": self.temperature,
                    "processing_time": duration,
                    "original_length": len(content),
                    "rewritten_length": len(rewritten),
                },
            }
        except Exception as e:
            duration = time.perf_counter() - start
            raise RuntimeError(
                f"WriterAgent generation failed: {e}\n\n"
                "If you see PERMISSION_DENIED, your Gemini API key may be "
                "invalid or revoked. Please set a valid GEMINI_API_KEY."
            )
