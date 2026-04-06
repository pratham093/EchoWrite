"""
Content Selection Engine (Inference) — Uses the Reward Model to pick
the highest-reward content variant, with ε-greedy exploration so the
system keeps discovering better parameter combinations.
"""

import numpy as np
from typing import List, Dict, Optional

from rl_models.reward_model import RewardModel
from agents.writer import WriterAgent
from agents.reviewer_agent import ReviewerAgent


class ContentSelectionEngine:
    """
    1. Generate N content variants (different styles).
    2. Have the ReviewerAgent score each.
    3. Select the best via reward model (with exploration).
    """

    STYLE_POOL = ["engaging", "professional", "creative", "concise", "casual", "academic"]

    def __init__(
        self,
        reward_model: Optional[RewardModel] = None,
        exploration_rate: float = 0.1,
    ):
        self.reward_model = reward_model or RewardModel()
        self.exploration_rate = exploration_rate
        self.writer = WriterAgent()
        self.reviewer = ReviewerAgent()

    # ------------------------------------------------------------------
    # Core pipeline
    # ------------------------------------------------------------------
    def generate_multiple_versions(
        self,
        content: str,
        n_versions: int = 3,
        styles: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Produce *n_versions* rewrites of *content*, each in a randomly
        chosen style (or from the supplied list), and attach AI reviews.
        """
        chosen_styles = styles or list(
            np.random.choice(self.STYLE_POOL, size=min(n_versions, len(self.STYLE_POOL)), replace=False)
        )

        versions: List[Dict] = []
        for i in range(n_versions):
            style = chosen_styles[i % len(chosen_styles)]
            try:
                result = self.writer.rewrite_content(content, style=style)
                review = self.reviewer.review_content(content, result["rewritten"])
                versions.append(
                    {
                        "content": result["rewritten"],
                        "style": style,
                        "ai_review": review,
                        "metadata": result["metadata"],
                        "predicted_quality": self.reward_model.predict_quality(
                            result["rewritten"], {"style": style}
                        ),
                    }
                )
            except Exception as e:
                print(f"⚠️  Version generation failed (style={style}): {e}")
        return versions

    def select_best_version(self, versions: List[Dict]) -> Dict:
        """
        ε-greedy selection:
          • With probability ε → pick a random version (exploration).
          • Otherwise → pick the version with the highest reward (exploitation).
        """
        if not versions:
            raise ValueError("No versions to select from")

        # Exploration
        if np.random.random() < self.exploration_rate:
            idx = int(np.random.randint(len(versions)))
            versions[idx]["selection_reason"] = "exploration"
            return versions[idx]

        # Exploitation
        rewards = [
            self.reward_model.calculate_reward(
                v["content"],
                v.get("ai_review", {}),
                v.get("human_feedback"),
            )
            for v in versions
        ]
        best_idx = int(np.argmax(rewards))
        versions[best_idx]["selection_reason"] = "exploitation"
        versions[best_idx]["reward_score"] = rewards[best_idx]
        return versions[best_idx]

    # ------------------------------------------------------------------
    # Convenience: generate → select in one call
    # ------------------------------------------------------------------
    def generate_and_select(
        self,
        content: str,
        n_versions: int = 3,
    ) -> Dict:
        """End-to-end: generate N versions, pick the best one."""
        versions = self.generate_multiple_versions(content, n_versions)
        if not versions:
            raise RuntimeError("All version generations failed")
        best = self.select_best_version(versions)
        best["all_versions"] = versions  # attach siblings for transparency
        return best
