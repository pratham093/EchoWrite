import os
import json
import hashlib
from datetime import datetime

class RewardModel:
    def __init__(self, data_path: str = "./reward_data"):
        os.makedirs(data_path, exist_ok=True)
        self.data_path = data_path
        self.learning_history = self.load_history()
        self.style_preferences = {}

    def record_feedback(self, version_id: str, content: str, metadata: dict, human_rating: float, human_feedback: str):
        feedback_entry = {
            'version_id': str(version_id),
            'timestamp': datetime.now().isoformat(),
            'content_length': len(content),
            'style': metadata.get('style', 'unknown'),
            'ai_scores': metadata.get('ai_scores', {}),
            'human_rating': float(human_rating),
            'human_feedback': human_feedback,
            'iteration_count': metadata.get('iteration_count', 1)
        }
        self.learning_history.append(feedback_entry)
        self.save_history()
        self.update_weights()

    def update_weights(self):
        style_ratings = {}
        for entry in self.learning_history:
            style = entry['style']
            style_ratings.setdefault(style, []).append(entry['human_rating'])
        self.style_preferences = {s: sum(r)/len(r) for s, r in style_ratings.items() if r}

    def predict_quality(self, content: str, metadata: dict) -> float:
        if not self.learning_history:
            return 0.5
        style = metadata.get('style', 'unknown')
        scores = [e['human_rating'] for e in self.learning_history if e['style']==style]
        return sum(scores)/len(scores) if scores else 0.5

    def get_best_parameters(self) -> dict:
        if not self.learning_history:
            return {'style':'engaging','iterations':2,'avg_score':0.0}
        style_scores = {}
        iter_scores = {}
        for entry in self.learning_history:
            s=entry['style']; r=entry['human_rating']; c=entry['iteration_count']
            style_scores.setdefault(s,[]).append(r)
            iter_scores.setdefault(c,[]).append(r)
        best_style = max(style_scores, key=lambda s: sum(style_scores[s])/len(style_scores[s]))
        best_iter = max(iter_scores, key=lambda i: sum(iter_scores[i])/len(iter_scores[i]))
        return {'style':best_style,'iterations':best_iter,'avg_score':sum(style_scores[best_style])/len(style_scores[best_style])}

    def save_history(self):
        with open(os.path.join(self.data_path,"learning_history.json"),'w') as f:
            json.dump(self.learning_history,f,indent=2)

    def load_history(self) -> list:
        path=os.path.join(self.data_path,"learning_history.json")
        if os.path.exists(path):
            return json.load(open(path))
        return []

    def calculate_reward(self, content: str, ai_review: dict, human_feedback: dict=None) -> float:
        scores=[ai_review.get(k,0) for k in ['quality_score','clarity_score','engagement_score','accuracy_score'] if ai_review.get(k,0)>0]
        base = sum(scores)/len(scores)/10 if scores else 0.5
        if human_feedback and 'rating' in human_feedback:
            return 0.7*human_feedback['rating']+0.3*base
        return base

    def get_statistics(self) -> dict:
        if not self.learning_history:
            return {'total_feedback':0,'average_rating':0,'best_style':'unknown','styles_tested':0}
        ratings=[e['human_rating'] for e in self.learning_history]
        styles=set(e['style'] for e in self.learning_history)
        style_detail={s:{'count':len([e for e in self.learning_history if e['style']==s]),'average':sum(e['human_rating'] for e in self.learning_history if e['style']==s)} for s in styles}
        best_style=max(style_detail, key=lambda s:style_detail[s]['average'])
        return {'total_feedback':len(ratings),'average_rating':sum(ratings)/len(ratings),'best_style':best_style,'styles_tested':len(styles),'style_details':style_detail}

SimpleRewardModel = RewardModel
