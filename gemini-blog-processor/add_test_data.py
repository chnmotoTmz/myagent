"""
blog_seedテーブルにテストデータを追加するスクリプト
"""
import os
import sys
import sqlite3
from datetime import datetime

# データベースファイルの絶対パス
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance', 'app.db'))
print(f"データベースパス: {db_path}")

def insert_test_data():
    """テスト用のブログデータを追加"""
    try:
        # データベースファイルが存在するか確認
        if not os.path.exists(db_path):
            print(f"エラー: データベースファイルが見つかりません: {db_path}")
            return

        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # blog_seedテーブルが存在するか確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='blog_seed'")
        if not cursor.fetchone():
            print("エラー: blog_seedテーブルが存在しません")
            return
        
        # 現在日時
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # テストデータの準備
        test_data = [
            {
                'hour_key': '2025050600',
                'markdown_content': """# 2025年5月6日のブログ記事

こんにちは！これは統合テスト用のブログ記事です。Gemini APIを使って自動生成されたコンテンツの例としてこのデータが表示されています。

## 今日のトピック
- 統合テストの実施
- WebhookとAPI連携の検証
- データ処理フローの確認

画像処理も正常に動作しており、今後はAIによる画像分析結果も含まれる予定です。
""",
                'created_at': now,
                'updated_at': now
            },
            {
                'hour_key': '2025050606',
                'markdown_content': """# 2025年5月6日午前6時のブログ更新

朝のアップデートです。システムは一晩中安定して動作しています。

## 統計情報
- 処理メッセージ数: 24
- エラー発生数: 0
- 平均応答時間: 1.2秒

今日も引き続き監視を続けていきます。
""",
                'created_at': now,
                'updated_at': now
            }
        ]
        
        # データ挿入
        for item in test_data:
            cursor.execute(
                'INSERT INTO blog_seed (hour_key, markdown_content, created_at, updated_at) VALUES (?, ?, ?, ?)',
                (item['hour_key'], item['markdown_content'], item['created_at'], item['updated_at'])
            )
        
        # コミット
        conn.commit()
        print(f"blog_seedテーブルに {len(test_data)} 件のテストデータを追加しました")
        
        # 確認のため全データを表示
        cursor.execute('SELECT hour_key, created_at FROM blog_seed')
        rows = cursor.fetchall()
        print("\n現在のデータ:")
        for row in rows:
            print(f"hour_key: {row[0]}, created_at: {row[1]}")
        
    except sqlite3.Error as e:
        print(f"SQLiteエラー: {e}")
    except Exception as e:
        print(f"エラー: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    insert_test_data()