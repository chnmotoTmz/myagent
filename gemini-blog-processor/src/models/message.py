# /home/ubuntu/gemini_blog_processor/src/models/message.py
"""LINEメッセージを保存するためのデータモデル"""

from src.database import db
from datetime import datetime, timezone
from typing import Dict, Any

class Message(db.Model):
    """LINEメッセージを表すデータモデル
    
    Attributes:
        message_id: メッセージの一意識別子
        user_id: メッセージを送信したユーザーのID
        message_type: メッセージの種類（text, image, etc.）
        content: メッセージの内容
        timestamp: メッセージの受信時刻
    """
    
    message_id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    message_type = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs: Any) -> None:
        """モデルの初期化
        
        Args:
            **kwargs: モデルの属性と値
        """
        kwargs.setdefault('timestamp', datetime.now(timezone.utc))
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """モデルの文字列表現"""
        return f"<Message {self.message_id[:8]}... from {self.user_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """モデルを辞書形式に変換
        
        Returns:
            Dict[str, Any]: モデルの属性と値を含む辞書
        """
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }

