from datetime import datetime
from typing import Dict, Any, Optional
import json
from .database import AmebaDatabase
from .exceptions import PostNotFoundError

class PostConverter:
    """ブログ記事を指定されたJSONフォーマットに変換するクラス"""
    
    def __init__(self, db: AmebaDatabase):
        self.db = db
    
    def convert_post(self, post_id: str) -> Dict[str, Any]:
        """記事を指定されたJSONフォーマットに変換
        
        Args:
            post_id: 記事ID
            
        Returns:
            Dict[str, Any]: 変換後のJSONデータ
            
        Raises:
            PostNotFoundError: 記事が見つからない場合
        """
        # データベースから記事を取得
        post = self.db.get_post(post_id)
        if not post:
            raise PostNotFoundError(f"記事が見つかりません: {post_id}")
        
        # 作成日時と更新日時を取得
        created_at = datetime.fromisoformat(post.get('created_at', datetime.now().isoformat()))
        updated_at = datetime.fromisoformat(post.get('updated_at', created_at.isoformat()))
        published_at = datetime.fromisoformat(post.get('published_at', updated_at.isoformat()))
        
        # メタデータの作成
        meta = {
            'title': post.get('title', ''),
            'description': post.get('description', ''),
            'permalink': post.get('permalink', ''),
            'category': post.get('category', ''),
            'tags': post.get('tags', []),
            'author': {
                'id': post.get('author_id', ''),
                'name': post.get('author_name', ''),
                'image_url': post.get('author_image_url', '')
            },
            'thumbnail': {
                'url': post.get('thumbnail_url', ''),
                'alt': post.get('thumbnail_alt', ''),
                'width': post.get('thumbnail_width', 0),
                'height': post.get('thumbnail_height', 0),
                'type': post.get('thumbnail_type', '')
            },
            'seo': {
                'focus_keyword': post.get('seo_focus_keyword', ''),
                'custom_title': post.get('seo_custom_title', ''),
                'custom_description': post.get('seo_custom_description', ''),
                'no_index': post.get('seo_no_index', False),
                'canonical_url': post.get('seo_canonical_url', '')
            }
        }
        
        # コンテンツデータの作成
        content = {
            'format': post.get('content_format', 'markdown'),
            'body': post.get('content', '')
        }
        
        # 最終的なJSONデータの作成
        json_data = {
            'post_id': post_id,
            'platform': post.get('platform', 'hatena-blog'),
            'status': post.get('status', 'published'),
            'visibility': post.get('visibility', 'public'),
            'created_at': created_at.isoformat(),
            'updated_at': updated_at.isoformat(),
            'published_at': published_at.isoformat(),
            'meta': meta,
            'content': content
        }
        
        return json_data
    
    def save_as_json(self, post_id: str, output_path: str) -> None:
        """変換したJSONデータをファイルに保存
        
        Args:
            post_id: 記事ID
            output_path: 出力ファイルパス
        """
        json_data = self.convert_post(post_id)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2) 