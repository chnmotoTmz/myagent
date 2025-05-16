"""
アプリケーション全体で使用する設定を管理するモジュール
.envファイルから環境変数をロードし、アプリケーション全体で使用可能にします
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# アプリケーションのルートパスを取得
ROOT_DIR = Path(__file__).parent.parent.absolute()

# .envファイルのパス
ENV_FILE = os.path.join(ROOT_DIR, '.env')

# .envファイルが存在する場合は読み込み
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
    logging.info(f"環境変数を {ENV_FILE} からロードしました")
else:
    logging.warning(f".envファイルが見つかりません: {ENV_FILE}")

# Gemini API設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", 60))

# データベース設定
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/app.db")

# サーバー設定
PORT = int(os.environ.get("PORT", 8001))
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "t")
SECRET_KEY = os.environ.get("SECRET_KEY", "a_secure_random_secret_key_here")

# 外部サービス連携設定
LINE_WEBHOOK_URL = os.environ.get("LINE_WEBHOOK_URL", "http://localhost:8083/webhook")
RETRY_MAX_ATTEMPTS = int(os.environ.get("RETRY_MAX_ATTEMPTS", 3))
RETRY_DELAY_SECONDS = int(os.environ.get("RETRY_DELAY_SECONDS", 5))

# Redmine連携設定
REDMINE_API_URL = os.environ.get("REDMINE_API_URL", "https://test-api.redmine-agent.example.com")
REDMINE_API_KEY = os.environ.get("REDMINE_API_KEY", "test_api_key_2025_05_17")
REDMINE_TIMEOUT = int(os.environ.get("REDMINE_TIMEOUT", 30))  # 30秒
REDMINE_MAX_RETRIES = int(os.environ.get("REDMINE_MAX_RETRIES", 3)) # Max retries for Redmine API calls
REDMINE_RETRY_DELAY_SECONDS = int(os.environ.get("REDMINE_RETRY_DELAY_SECONDS", 5)) # Delay between retries in seconds
REDMINE_INTEGRATION_ENABLED = os.environ.get("REDMINE_INTEGRATION_ENABLED", "True").lower() in ("true", "1", "t")

# ログ設定
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()

# アプリケーション設定
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16777216))  # 16MB