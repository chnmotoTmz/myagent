"""
pickleを使用したデータ永続化モジュール
"""
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import threading
from .exceptions import DatabaseError, PostNotFoundError
from .config import config

logger = logging.getLogger(__name__)

class AmebaDatabase:
    """Amebaブログ投稿データを管理するクラス（pickle版）"""
    
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or config.database.path)
        self.lock = threading.Lock()
        self.data = {
            'posts': [],
            'local_posts': []
        }
        self._load_data()

    def _load_data(self):
        """データをファイルから読み込む"""
        if self.db_path.exists():
            try:
                with self.lock, open(self.db_path, 'rb') as f:
                    self.data = pickle.load(f)
                logger.info(f"データを読み込みました: {self.db_path}")
            except Exception as e:
                raise DatabaseError(f"データ読み込みエラー: {e}")

    def _save_data(self):
        """データをファイルに保存する"""
        try:
            with self.lock, open(self.db_path, 'wb') as f:
                pickle.dump(self.data, f)
        except Exception as e:
            raise DatabaseError(f"データ保存エラー: {e}")

    def add_post(self, post_data: Dict[str, Any]):
        """投稿を追加または更新"""
        existing = next((p for p in self.data['posts'] if p['id'] == post_data['id']), None)
        if existing:
            existing.update(post_data)
        else:
            self.data['posts'].append(post_data)
        self._save_data()
        logger.info(f"投稿を追加/更新しました: {post_data['title']}")

    def get_post(self, post_id: str) -> Dict[str, Any]:
        """投稿を取得"""
        post = next((p for p in self.data['posts'] if p['id'] == post_id), None)
        if not post:
            raise PostNotFoundError(f"投稿が見つかりません: {post_id}")
        return post

    def get_all_posts(self) -> List[Dict[str, Any]]:
        """すべての記事を取得"""
        return self.data['posts']

    def delete_post(self, post_id: str):
        """投稿を削除"""
        initial_count = len(self.data['posts'])
        self.data['posts'] = [p for p in self.data['posts'] if p['id'] != post_id]
        if len(self.data['posts']) == initial_count:
            raise PostNotFoundError(f"投稿が見つかりません: {post_id}")
        self._save_data()
        logger.info(f"投稿を削除しました: {post_id}")

    def update_post_content(self, post_id: str, new_content: str):
        """記事の内容を更新"""
        post = self.get_post(post_id)
        post['content'] = new_content
        post['updated_at'] = datetime.now().isoformat()
        self._save_data()

    def get_local_posts(self) -> List[Dict[str, Any]]:
        """ローカルの投稿を取得"""
        return self.data['local_posts']

    def add_local_post(self, title: str, content: str):
        """ローカル投稿を追加"""
        new_post = {
            'id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'title': title,
            'content': content,
            'created_at': datetime.now().isoformat()
        }
        self.data['local_posts'].append(new_post)
        self._save_data()
        logger.info(f"ローカル投稿を追加しました: {title}")

    def delete_local_post(self, post_id: str):
        """ローカル投稿を削除"""
        initial_count = len(self.data['local_posts'])
        self.data['local_posts'] = [p for p in self.data['local_posts'] if p['id'] != post_id]
        if len(self.data['local_posts']) == initial_count:
            raise PostNotFoundError(f"ローカル投稿が見つかりません: {post_id}")
        self._save_data()
        logger.info(f"ローカル投稿を削除しました: {post_id}")

    def get_post_list(self, include_content: bool = False) -> List[Dict[str, Any]]:
        """
        記事一覧を取得
        
        Args:
            include_content (bool): 本文を含めるかどうか
            
        Returns:
            List[Dict[str, Any]]: 記事データのリスト
        """
        return self.data['posts'] if include_content else [p for p in self.data['posts'] if p.get('status') == '取得済み']

    def add_posts_to_list(self, posts: List[Dict[str, Any]]):
        """
        記事一覧に記事を追加
        
        Args:
            posts (List[Dict[str, Any]]): 追加する記事のリスト
        """
        self.data['posts'].extend(posts)
        self._save_data()

    def create_local_post(self) -> int:
        """
        新規ローカル記事を作成
        
        Returns:
            int: 作成された記事のID
        """
        new_post = {
            'id': datetime.now().strftime("%Y%m%d%H%M%S"),
            'title': '新規記事',
            'content': '',
            'created_at': datetime.now().isoformat()
        }
        self.data['local_posts'].append(new_post)
        self._save_data()
        return int(new_post['id'])

    def has_local_edit(self, post_id: str) -> bool:
        """
        記事にローカル編集があるかどうかを確認
        
        Args:
            post_id (str): 記事ID
            
        Returns:
            bool: ローカル編集がある場合はTrue
        """
        return any(p['id'] == post_id for p in self.data['local_posts'] if p.get('status') == '編集中')

    def has_content(self, post_id: str) -> bool:
        """
        記事に本文があるかどうかを確認
        
        Args:
            post_id (str): 記事ID
            
        Returns:
            bool: 本文がある場合はTrue
        """
        return any(p['id'] == post_id for p in self.data['posts'] if p.get('content'))

def main():
    """テスト・デモンストレーション用のメイン関数"""
    logging.basicConfig(level=logging.INFO)
    
    db = AmebaDatabase("ameba_posts.pkl")
    
    # テスト記事の追加
    print("テスト記事を追加します...")
    db.add_local_post("テスト記事", "これはテスト記事の内容です。")
    
    # 記事一覧の表示
    print("\nローカル記事一覧:")
    posts = db.get_local_posts()
    for post in posts:
        print(f"{post['id']}: {post['title']} ({post['created_at']})")
    
if __name__ == "__main__":
    main()
