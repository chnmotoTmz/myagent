"""
データベースの内容を確認するシンプルなスクリプト
"""
import os
import sqlite3

# データベースファイルの絶対パス
db_path = os.path.abspath(os.path.join('instance', 'app.db'))
print(f"データベースパス: {db_path}")

if not os.path.exists(db_path):
    print(f"エラー: データベースファイルが見つかりません: {db_path}")
    exit(1)

try:
    # データベース接続
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 利用可能なテーブルを一覧表示
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("データベース内のテーブル:")
    for table in tables:
        print(f"- {table[0]}")
    
    # blog_seedテーブルの構造を表示
    print("\nblog_seedテーブルのスキーマ:")
    cursor.execute("PRAGMA table_info(blog_seed)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # blog_seedテーブルのデータを表示
    print("\nblog_seedテーブルの内容:")
    cursor.execute("SELECT * FROM blog_seed")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"ID: {row[0]}, hour_key: {row[1]}, created_at: {row[3]}")
            print(f"  最初の100文字の内容: {row[2][:100]}...\n")
    else:
        print("  テーブルにデータがありません")
    
    # フォールバック - 直接データを挿入
    if len(rows) == 0:
        print("\nテーブルが空のため、直接SQLを使用してテストデータを追加します...")
        try:
            cursor.execute("""
            INSERT INTO blog_seed (hour_key, markdown_content, created_at, updated_at) 
            VALUES (?, ?, datetime('now'), datetime('now'))
            """, ('2025050600', '# 2025年5月6日のテスト記事\n\nこれは直接SQLで追加したテストデータです。'))
            conn.commit()
            print("テストデータを追加しました！")
            
            # 追加後に再確認
            cursor.execute("SELECT * FROM blog_seed")
            rows = cursor.fetchall()
            print("\n追加後のblog_seedテーブルの内容:")
            for row in rows:
                print(f"ID: {row[0]}, hour_key: {row[1]}, created_at: {row[3]}")
        except sqlite3.Error as e:
            print(f"SQLエラー: {e}")
    
except sqlite3.Error as e:
    print(f"SQLiteエラー: {e}")
finally:
    if conn:
        conn.close()