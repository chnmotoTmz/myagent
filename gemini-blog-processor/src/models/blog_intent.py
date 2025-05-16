"""
ブログ記事の意図分析結果を保存するモデル
"""
import datetime
from datetime import timezone
from typing import Dict, Any

from src.database import db

class BlogIntentAnalysis(db.Model):
    """ブログ記事の意図分析結果を保存するテーブル"""
    
    id = db.Column(db.Integer, primary_key=True)
    # blog_seedテーブルとの関連付け
    hour_key = db.Column(db.String(12), db.ForeignKey('blog_seed.hour_key'), nullable=False)
    # 分析結果
    intent_category = db.Column(db.String(50), nullable=False)  # 意図カテゴリ
    intent_description = db.Column(db.Text, nullable=False)     # 意図の詳細説明
    confidence_score = db.Column(db.Float, nullable=False)      # 確信度スコア
    target_audience = db.Column(db.String(100))                 # ターゲットオーディエンス
    emotional_tone = db.Column(db.String(50))                   # 感情的トーン
    call_to_action = db.Column(db.Text)                         # 想定されるアクション
    raw_response = db.Column(db.Text)                           # Gemini APIからの生の応答
    # メタデータ
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.datetime.now(timezone.utc), 
                          onupdate=datetime.datetime.now(timezone.utc))
    
    # リレーションシップ
    blog_seed = db.relationship('BlogSeed', backref=db.backref('intent_analysis', lazy=True))
    
    def to_dict(self) -> Dict[str, Any]:
        """オブジェクトをディクショナリに変換"""
        return {
            'id': self.id,
            'hour_key': self.hour_key,
            'intent_category': self.intent_category,
            'intent_description': self.intent_description,
            'confidence_score': self.confidence_score,
            'target_audience': self.target_audience,
            'emotional_tone': self.emotional_tone,
            'call_to_action': self.call_to_action,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }