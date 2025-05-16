"""
環境変数デバッグスクリプト
.envファイルの読み込みをテストし、環境変数の値を表示します。
"""

import os
from dotenv import load_dotenv, find_dotenv

# .envファイルの読み込み (詳細モード)
print("環境変数デバッグ情報:")
print("-" * 50)

# .envファイルを明示的に検索
dotenv_path = find_dotenv(usecwd=True)
print(f"検出された.envファイルのパス: {dotenv_path}")
print(f"ファイルは存在しますか？ {os.path.exists(dotenv_path)}")

# ファイルの内容を読み取り
if os.path.exists(dotenv_path):
    print("\n.envファイルの内容 (PORT設定のみ):")
    with open(dotenv_path, 'r') as f:
        for line in f:
            if "PORT=" in line:
                print(f"  > {line.strip()}")

# 明示的にロード
print("\n.envファイルをロードします...")
loaded = load_dotenv(dotenv_path)
print(f"ロード成功: {loaded}")

# 環境変数を表示
print("\n現在の環境変数の値:")
env_vars = ["HOST", "PORT", "DEBUG"]
for var in env_vars:
    print(f"{var}: {os.getenv(var)}")

print("-" * 50)
print("この問題を解決するために:")
print("1. コマンドライン引数で直接ポートを指定する: uvicorn app.main:app --host 0.0.0.0 --port 8080")
print("2. あるいはshell変数として設定: $env:PORT=8080")
print("-" * 50)
