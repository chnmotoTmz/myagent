#!/usr/bin/env python3
"""
モード切り替えツール

開発モードと本番モードを切り替えるためのユーティリティ
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# アプリケーションのパスを追加
app_path = str(Path(__file__).parent)
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def switch_mode(mode: str) -> None:
    """
    システム動作モードを切り替える
    
    Args:
        mode: 'dev' または 'prod'
    """
    if mode not in ["dev", "prod"]:
        logger.error("モードは 'dev' または 'prod' を指定してください。")
        return
        
    from dotenv import load_dotenv, set_key
    
    # .envファイルのパス
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        logger.error(f".envファイルが見つかりません: {env_path}")
        return
    
    # 現在の設定を読み込み
    load_dotenv(env_path)
    current_debug = os.getenv("DEBUG", "True")
    
    # 新しいモードを設定
    is_dev = mode == "dev"
    mode_name = "開発モード" if is_dev else "本番モード"
    debug_value = "True" if is_dev else "False"
    log_level = "DEBUG" if is_dev else "INFO"
    
    # 変更がある場合のみ更新
    if current_debug != debug_value:
        set_key(env_path, "DEBUG", debug_value)
        set_key(env_path, "LOG_LEVEL", log_level)
        logger.info(f"システム動作モードを {mode_name} に切り替えました")
        
        # 設定ファイルも更新
        try:
            from app.config import set_config
            set_config("system.environment", "development" if is_dev else "production")
            set_config("system.debug_mode", is_dev)
            logger.info("設定ファイルを更新しました")
        except ImportError:
            logger.warning("設定モジュールが読み込めないため、設定ファイルは更新されていません")
    else:
        logger.info(f"システムは既に {mode_name} で動作しています")

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="Redmineエージェントの動作モードを切り替えます")
    parser.add_argument("mode", choices=["dev", "prod"], help="設定するモード (dev=開発モード, prod=本番モード)")
    parser.add_argument("--status", action="store_true", help="現在のモードを表示するのみ")
    
    args = parser.parse_args()
    
    if args.status:
        # 現在のモードを表示
        from dotenv import load_dotenv
        load_dotenv()
        is_dev = os.getenv("DEBUG", "True").lower() == "true"
        mode_name = "開発モード" if is_dev else "本番モード"
        print(f"現在の動作モード: {mode_name}")
        return
    
    # モードの切り替え
    switch_mode(args.mode)

if __name__ == "__main__":
    main()
