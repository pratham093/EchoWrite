import numpy as np
from typing import List, Dict
from .reward_model import RewardModel  # Use relative import
from agents.reviewer_agent import ReviewerAgent
from agents.writer import WriterAgent

class ContentSelectionEngine:
    def __init__(self, reward_model: RewardModel, exploration_rate: float = 0.1):
        self.reward_model = reward_model
        self.exploration_rate = exploration_rate

    def select_best_version(self, versions: List[Dict]) -> Dict:
        if np.random.random() < self.exploration_rate:
            return np.random.choice(versions)
        rewards = [
            self.reward_model.calculate_reward(
                v['content'],
                v.get('ai_review', {}),
                v.get('human_feedback', {})
            ) for v in versions
        ]
        best_idx = int(np.argmax(rewards))
        return versions[best_idx]

    def generate_multiple_versions(self, content: str, n_versions: int = 3) -> List[Dict]:
        styles = ["engaging", "professional", "creative", "concise", "detailed"]
        writer = WriterAgent()
        reviewer = ReviewerAgent()
        versions = []
        for _ in range(n_versions):
            style = np.random.choice(styles)
            result = writer.rewrite_content(content, style=style)
            review = reviewer.review_content(content, result['rewritten'])
            versions.append({
                'content': result['rewritten'],
                'style': style,
                'ai_review': review
            })
        return versions
