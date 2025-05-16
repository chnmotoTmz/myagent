"""
Flaskアプリケーションコンテキスト内でblog_seedテーブルにテストデータを追加するスクリプト
"""
import os
import sys
from datetime import datetime
import traceback

# アプリケーションのルートディレクトリを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print(f"現在の作業ディレクトリ: {os.getcwd()}")
print(f"Pythonパス: {sys.path}")
instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
db_path = os.path.join(instance_dir, 'app.db')
print(f"データベースファイルのパス: {db_path}")
print(f"データベースファイルは存在します: {os.path.exists(db_path)}")

try:
    # Flaskアプリケーションとモデルをインポート
    print("Flaskアプリのインポートを試みます...")
    from src.main import app
    from src.database import db
    from src.models.blog_seed import BlogSeed
    print("Flaskアプリのインポートに成功しました")
except Exception as e:
    print(f"インポートエラー: {e}")
    traceback.print_exc()
    sys.exit(1)

def add_test_data():
    """Flaskアプリケーションコンテキスト内でテストデータを追加"""
    print("アプリケーションコンテキストを作成します...")
    with app.app_context():
        try:
            # テーブル構造を確認
            print("データベースのテーブル構造を確認します...")
            tables = db.engine.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            print(f"データベース内のテーブル: {[table[0] for table in tables]}")
            
            # BlogSeedテーブルの構造を確認
            try:
                columns = db.engine.execute("PRAGMA table_info(blog_seed)").fetchall()
                print("blog_seedテーブルの構造:")
                for col in columns:
                    print(f"  {col[1]} ({col[2]})")
            except Exception as e:
                print(f"テーブル構造の確認中にエラー: {e}")
            
            # 既存データをチェック
            print("既存のデータを確認します...")
            existing_seeds = BlogSeed.query.all()
            print(f"現在のblog_seedデータ数: {len(existing_seeds)}")

            # テストデータ
            print("テストデータを作成します...")
            now = datetime.now()
            test_entries = [
                BlogSeed(
                    hour_key='2025050600',
                    markdown_content="""# 2025年5月6日のブログ記事

こんにちは！これは統合テスト用のブログ記事です。Gemini APIを使って自動生成されたコンテンツの例です。

## 今日のトピック
- 統合テストの実施
- WebhookとAPI連携の検証
- データ処理フローの確認

画像処理も正常に動作しています。
""",
                    created_at=now,
                    updated_at=now
                ),
                BlogSeed(
                    hour_key='2025050606',
                    markdown_content="""# 2025年5月6日午前6時のブログ更新

朝のアップデートです。システムは安定して動作しています。

## 統計情報
- 処理メッセージ数: 24
- エラー発生数: 0
- 平均応答時間: 1.2秒
""",
                    created_at=now,
                    updated_at=now
                )
            ]

            # データを追加
            print("データベースに新しいエントリを追加します...")
            for entry in test_entries:
                db.session.add(entry)
            
            print("変更をコミットします...")
            db.session.commit()
            print(f"{len(test_entries)}件のテストデータをblog_seedテーブルに追加しました")

            # 追加したデータを確認
            seeds = BlogSeed.query.all()
            print(f"\n現在のデータ数: {len(seeds)}")
            for seed in seeds:
                print(f"ID: {seed.id}, hour_key: {seed.hour_key}, 作成日時: {seed.created_at}")

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            traceback.print_exc()
            db.session.rollback()
            return False
        
        return True

if __name__ == '__main__':
    success = add_test_data()
    if success:
        print("テストデータの追加に成功しました。")
        sys.exit(0)
    else:
        print("テストデータの追加に失敗しました。")
        sys.exit(1)