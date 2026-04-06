"""
Reward Model — Learns style preferences and quality predictions from
human feedback (RLHF-lite).  Persists learning history as JSON.
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from config.settings import settings


class RewardModel:
    """
    Tracks human ratings per style / iteration count and uses them to:
      • predict expected quality of new content
      • recommend best-performing parameters
      • compute blended AI + human reward signals
    """

    def __init__(self, data_path: str | None = None):
        self.data_path = data_path or settings.REWARD_DATA_DIR
        os.makedirs(self.data_path, exist_ok=True)
        self.learning_history: List[Dict[str, Any]] = self._load_history()
        self.style_preferences: Dict[str, float] = {}
        self._update_weights()

    # ------------------------------------------------------------------
    # Record & learn
    # ------------------------------------------------------------------
    def record_feedback(
        self,
        version_id: str,
        content: str,
        metadata: dict,
        human_rating: float,
        human_feedback: str = "",
    ):
        """Append one human-feedback entry and re-compute weights."""
        entry = {
            "version_id": str(version_id),
            "timestamp": datetime.now().isoformat(),
            "content_length": len(content),
            "style": metadata.get("style", "unknown"),
            "ai_scores": metadata.get("ai_scores", {}),
            "human_rating": float(human_rating),
            "human_feedback": human_feedback,
            "iteration_count": metadata.get("iteration_count", 1),
        }
        self.learning_history.append(entry)
        self._save_history()
        self._update_weights()

    def _update_weights(self):
        buckets: Dict[str, List[float]] = {}
        for e in self.learning_history:
            buckets.setdefault(e["style"], []).append(e["human_rating"])
        self.style_preferences = {s: sum(r) / len(r) for s, r in buckets.items() if r}

    # ------------------------------------------------------------------
    # Predict & recommend
    # ------------------------------------------------------------------
    def predict_quality(self, content: str, metadata: dict) -> float:
        """Predict expected human rating based on historical data."""
        if not self.learning_history:
            return 0.5
        style = metadata.get("style", "unknown")
        scores = [e["human_rating"] for e in self.learning_history if e["style"] == style]
        return sum(scores) / len(scores) if scores else 0.5

    def get_best_parameters(self) -> dict:
        """Return the style + iteration count that historically performs best."""
        if not self.learning_history:
            return {"style": "engaging", "iterations": 2, "avg_score": 0.0}

        style_scores: Dict[str, List[float]] = {}
        iter_scores: Dict[int, List[float]] = {}
        for e in self.learning_history:
            style_scores.setdefault(e["style"], []).append(e["human_rating"])
            iter_scores.setdefault(e["iteration_count"], []).append(e["human_rating"])

        best_style = max(style_scores, key=lambda s: sum(style_scores[s]) / len(style_scores[s]))
        best_iter = max(iter_scores, key=lambda i: sum(iter_scores[i]) / len(iter_scores[i]))
        avg = sum(style_scores[best_style]) / len(style_scores[best_style])
        return {"style": best_style, "iterations": best_iter, "avg_score": avg}

    # ------------------------------------------------------------------
    # Reward calculation (blended AI + human)
    # ------------------------------------------------------------------
    def calculate_reward(
        self,
        content: str,
        ai_review: dict,
        human_feedback: Optional[dict] = None,
    ) -> float:
        """
        Compute a 0-1 reward.
        If human feedback is available it dominates (weighted by settings.HUMAN_WEIGHT).
        """
        score_keys = ("quality_score", "clarity_score", "engagement_score", "accuracy_score")
        raw = [ai_review.get(k, 0) for k in score_keys if ai_review.get(k, 0) > 0]
        base = (sum(raw) / len(raw) / 10) if raw else 0.5

        if human_feedback and "rating" in human_feedback:
            return settings.HUMAN_WEIGHT * human_feedback["rating"] + settings.AI_WEIGHT * base
        return base

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def get_statistics(self) -> dict:
        if not self.learning_history:
            return {
                "total_feedback": 0,
                "average_rating": 0,
                "best_style": "unknown",
                "styles_tested": 0,
            }
        ratings = [e["human_rating"] for e in self.learning_history]
        styles = set(e["style"] for e in self.learning_history)
        style_detail = {}
        for s in styles:
            entries = [e for e in self.learning_history if e["style"] == s]
            total = sum(e["human_rating"] for e in entries)
            style_detail[s] = {"count": len(entries), "average": total / len(entries)}
        best = max(style_detail, key=lambda s: style_detail[s]["average"])
        return {
            "total_feedback": len(ratings),
            "average_rating": sum(ratings) / len(ratings),
            "best_style": best,
            "styles_tested": len(styles),
            "style_details": style_detail,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _history_path(self) -> str:
        return os.path.join(self.data_path, "learning_history.json")

    def _save_history(self):
        with open(self._history_path(), "w") as f:
            json.dump(self.learning_history, f, indent=2)

    def _load_history(self) -> list:
        path = self._history_path()
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return []


# Alias for backward compat
SimpleRewardModel = RewardModel
