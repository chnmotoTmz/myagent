"""生成されたブログ記事の種を保存するデータモデル"""

from src.database import db
from datetime import datetime, timezone
from typing import Dict, Any

class BlogSeed(db.Model):
    """ブログ記事の種を表すデータモデル
    
    Attributes:
        hour_key: 記事の時間枠を示すキー（YYYYMMDDHH形式）
        markdown_content: 生成された記事の内容（Markdown形式）
        created_at: 記事が生成された時刻
        updated_at: 記事が最後に更新された時刻
    """
    
    hour_key = db.Column(db.String(10), primary_key=True)
    markdown_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs: Any) -> None:
        """モデルの初期化
        
        Args:
            **kwargs: モデルの属性と値
        """
        now = datetime.now(timezone.utc)
        kwargs.setdefault('created_at', now)
        kwargs.setdefault('updated_at', now)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """モデルの文字列表現"""
        return f"<BlogSeed {self.hour_key}>"

    def to_dict(self) -> Dict[str, Any]:
        """モデルを辞書形式に変換
        
        Returns:
            Dict[str, Any]: モデルの属性と値を含む辞書
        """
        return {
            "hour_key": self.hour_key,
            "content": self.markdown_content,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def update_content(self, content: str) -> None:
        """記事の内容を更新
        
        Args:
            content: 新しい記事の内容
        """
        self.markdown_content = content
        self.updated_at = datetime.now(timezone.utc)

