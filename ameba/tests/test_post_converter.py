import unittest
from datetime import datetime
import json
import os
from pathlib import Path
from ameba_automation.database import AmebaDatabase
from ameba_automation.post_converter import PostConverter

class TestPostConverter(unittest.TestCase):
    def setUp(self):
        """テストの前準備"""
        # テスト用のデータベースファイルを作成
        self.test_db_path = "test_ameba_posts.pkl"
        self.db = AmebaDatabase(self.test_db_path)
        
        # テスト用の記事データを作成
        self.test_post = {
            'id': '20250322-salaryman-life-ai-hacks',
            'title': '彩りある日常と最新AI技術を探る：単身赴任サラリーマンの生活ハック',
            'description': '単身赴任の日常をAI技術で効率化し、より充実させるためのアイデアを紹介。',
            'content': '# 彩りある日常と最新AI技術を探る\n\n単身赴任の生活は、家族との物理的な距離だけでなく、日常の',
            'created_at': '2025-03-22T10:30:00Z',
            'updated_at': '2025-03-22T14:45:00Z',
            'published_at': '2025-03-22T15:00:00Z',
            'platform': 'hatena-blog',
            'status': 'published',
            'visibility': 'public',
            'category': 'ライフハック',
            'tags': ['単身赴任', 'AI技術', '生活効率化'],
            'author_id': 'tanaka-tech',
            'author_name': '田中テック',
            'author_image_url': 'https://example.com/authors/tanaka.jpg',
            'thumbnail_url': 'https://example.com/images/salaryman-ai-life.jpg',
            'thumbnail_alt': 'AIアシスタントを活用する単身赴任サラリーマン',
            'thumbnail_width': 1200,
            'thumbnail_height': 630,
            'thumbnail_type': 'jpeg',
            'seo_focus_keyword': '単身赴任 AI 生活ハック',
            'seo_custom_title': '',
            'seo_custom_description': '',
            'seo_no_index': False,
            'seo_canonical_url': ''
        }
        
        # テスト用の記事をデータベースに追加
        self.db.add_post(self.test_post)
        
        # コンバーターの初期化
        self.converter = PostConverter(self.db)
        
        # テスト用の出力ディレクトリを作成
        self.test_output_dir = Path('test_output')
        self.test_output_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """テスト後の後処理"""
        # テスト用のファイルを削除
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        # テスト出力ディレクトリを削除
        if self.test_output_dir.exists():
            for file in self.test_output_dir.glob('*'):
                file.unlink()
            self.test_output_dir.rmdir()
    
    def test_convert_post(self):
        """記事の変換テスト"""
        # 記事を変換
        json_data = self.converter.convert_post(self.test_post['id'])
        
        # 基本フィールドの検証
        self.assertEqual(json_data['post_id'], self.test_post['id'])
        self.assertEqual(json_data['platform'], self.test_post['platform'])
        self.assertEqual(json_data['status'], self.test_post['status'])
        self.assertEqual(json_data['visibility'], self.test_post['visibility'])
        
        # 日時の検証
        self.assertEqual(json_data['created_at'], self.test_post['created_at'])
        self.assertEqual(json_data['updated_at'], self.test_post['updated_at'])
        self.assertEqual(json_data['published_at'], self.test_post['published_at'])
        
        # メタデータの検証
        meta = json_data['meta']
        self.assertEqual(meta['title'], self.test_post['title'])
        self.assertEqual(meta['description'], self.test_post['description'])
        self.assertEqual(meta['category'], self.test_post['category'])
        self.assertEqual(meta['tags'], self.test_post['tags'])
        
        # 作者情報の検証
        self.assertEqual(meta['author']['id'], self.test_post['author_id'])
        self.assertEqual(meta['author']['name'], self.test_post['author_name'])
        self.assertEqual(meta['author']['image_url'], self.test_post['author_image_url'])
        
        # サムネイル情報の検証
        self.assertEqual(meta['thumbnail']['url'], self.test_post['thumbnail_url'])
        self.assertEqual(meta['thumbnail']['alt'], self.test_post['thumbnail_alt'])
        self.assertEqual(meta['thumbnail']['width'], self.test_post['thumbnail_width'])
        self.assertEqual(meta['thumbnail']['height'], self.test_post['thumbnail_height'])
        self.assertEqual(meta['thumbnail']['type'], self.test_post['thumbnail_type'])
        
        # SEO情報の検証
        self.assertEqual(meta['seo']['focus_keyword'], self.test_post['seo_focus_keyword'])
        self.assertEqual(meta['seo']['custom_title'], self.test_post['seo_custom_title'])
        self.assertEqual(meta['seo']['custom_description'], self.test_post['seo_custom_description'])
        self.assertEqual(meta['seo']['no_index'], self.test_post['seo_no_index'])
        self.assertEqual(meta['seo']['canonical_url'], self.test_post['seo_canonical_url'])
        
        # コンテンツの検証
        self.assertEqual(json_data['content']['format'], 'markdown')
        self.assertEqual(json_data['content']['body'], self.test_post['content'])
    
    def test_save_as_json(self):
        """JSONファイル保存のテスト"""
        output_path = self.test_output_dir / 'test_output.json'
        
        # JSONファイルとして保存
        self.converter.save_as_json(self.test_post['id'], str(output_path))
        
        # ファイルが作成されたことを確認
        self.assertTrue(output_path.exists())
        
        # 保存されたJSONを読み込んで検証
        with open(output_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        
        # 基本フィールドの検証
        self.assertEqual(saved_data['post_id'], self.test_post['id'])
        self.assertEqual(saved_data['meta']['title'], self.test_post['title'])
    
    def test_post_not_found(self):
        """存在しない記事IDのテスト"""
        with self.assertRaises(PostNotFoundError):
            self.converter.convert_post('non-existent-post-id')

if __name__ == '__main__':
    unittest.main() 