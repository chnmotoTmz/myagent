#!/usr/bin/env python3
"""
ログユーティリティのテストスクリプト

Unicodeエンコーディングの問題が修正されたかをテストします。
"""

import sys
import logging
from pathlib import Path

# アプリケーションのパスを追加
app_path = str(Path(__file__).parent)
if app_path not in sys.path:
    sys.path.insert(0, app_path)

from app.log_utils import setup_logging

def test_unicode_logging():
    """Unicodeエンコーディングのテスト"""
    # ロギング設定
    setup_logging(log_file="logs/unicode_test.log", level=logging.INFO)
    logger = logging.getLogger("unicode_test")
    
    print("=== Unicode logging test ===")
    
    # 通常のテキスト
    logger.info("標準的なテキストです")
    
    # 絵文字を含むテキスト
    logger.info("タスク完了: ✅")
    logger.info("警告: ⚠️")
    logger.info("エラー: ❌")
    logger.info("重要: ⭐")
    
    # 様々なUnicode文字
    logger.info("複数の絵文字: 🔍 🔧 🚀 📝 📊 ✨ 🎯 🔔")
    logger.info("国旗: 🇯🇵 🇺🇸 🇬🇧 🇫🇷 🇨🇳")
    
    # ロング文字列
    long_message = "これは非常に長いメッセージです。" * 10 + " タスク完了: ✅"
    logger.info(long_message)
    
    print("ログファイル 'logs/unicode_test.log' でも確認してください。")
    print("=== テスト完了 ===")

if __name__ == "__main__":
    test_unicode_logging()
