"""
Redmineチケット管理エージェント - 実行スクリプト

アプリケーションを実行するためのエントリポイント。
"""

import os
import uvicorn
from dotenv import load_dotenv
import logging

# ロガーの設定
# アプリケーション全体で一貫したロギング設定を推奨しますが、
# ここでは run.py 専用の基本的な設定を行います。
# app.log_utils.setup_logging() を利用することも検討できます。
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

if __name__ == "__main__":    # .envファイルの読み込み
    load_dotenv()

    # 環境変数の値を表示
    host = os.getenv("HOST", "0.0.0.0")
    port_str = os.getenv("PORT", "8080")
    try:
        port = int(port_str)
    except ValueError:
        logger.warning(f"環境変数 PORT の値 '{port_str}' は不正なため、デフォルトの 8080 を使用します。")
        port = 8080

    debug_mode = os.getenv("DEBUG", "True").lower() == "true"

    if debug_mode:
        logging.getLogger().setLevel(logging.DEBUG) # ルートロガーのレベルをDEBUGに設定
        logger.debug(f".envファイルの場所: {os.path.abspath('.env')}")
        logger.debug(f".envファイルは存在しますか？ {os.path.exists('.env')}")
        logger.debug("読み込まれた環境変数:")
        logger.debug(f"  HOST: {host}")
        logger.debug(f"  PORT: {port}")
        logger.debug(f"  DEBUG: {debug_mode}")

    # 起動モードの表示
    mode_name = "開発モード" if debug_mode else "本番モード"
    logger.info(f"⚙️  Redmineチケット管理エージェント ({mode_name}) を起動します...")
    logger.info(f"🌐 サーバーアドレス: http://{host}:{port}")

    # リロードは開発モードのみ
    reload_enabled = debug_mode

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_enabled,
        log_level="debug" if debug_mode else "info"
    )
