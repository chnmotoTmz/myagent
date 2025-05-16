#!/usr/bin/env python3
"""
Gemini API接続確認スクリプト

Gemini APIへの接続状態を確認し、シンプルなテストを実行します。
"""

import os
import sys
import logging
from dotenv import load_dotenv
from pathlib import Path

# アプリケーションのパスを追加
app_path = str(Path(__file__).parent)
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

def check_api_connection():
    """
    APIへの接続状態を確認し、接続情報を表示します
    """
    try:
        # まずパッケージがインストールされているか確認
        try:
            import google.generativeai
            logger.info("google-generativeaiパッケージがインストールされています")
        except ImportError:
            logger.error("google-generativeaiパッケージがインストールされていません")
            logger.error("pip install google-generativeai")
            return False

        # LLMヘルパーをインポート
        from app.llm_helper import RedmineAssistant
        logger.info("モジュールのインポートに成功しました")
        
        # APIキーの確認
        api_keys = []
        for env_var in ["GEMINI_API_KEY", "GEMINI_API_KEY1", "GEMINI_API_KEY2", "GOOGLE_API_KEY"]:
            if os.getenv(env_var):
                api_keys.append(env_var)
        
        logger.info(f"検出されたAPIキー環境変数: {', '.join(api_keys) if api_keys else 'なし'}")
        
        if not api_keys:
            logger.error("APIキーが設定されていません。.envファイルのGEMINI_API_KEYを確認してください")
            return False
        
        # LLMアシスタントの初期化
        assistant = RedmineAssistant()
        
        # 接続テスト
        connected = assistant._test_api_connection()
        if connected:
            logger.info(f"✅ API接続成功（アクティブキー: #{assistant.current_key_index + 1}/{len(assistant.api_keys)}）")
            
            # 簡単なテストを実行
            test_input = "こんにちは、簡単なクエリでAPIをテストします"
            response = assistant._make_api_request(test_input, temperature=0.1)
            
            if response:
                text = assistant.extract_text_from_response(response)
                logger.info(f"テスト応答: {text[:100]}...")
                logger.info("全てのテストが成功しました")
                return True
            else:
                logger.error("APIレスポンスを取得できませんでした")
                return False
        else:
            logger.error("❌ API接続失敗")
            return False
            
    except ImportError as e:
        logger.error(f"モジュールのインポートに失敗しました: {e}")
        logger.error("google-generativeaiパッケージがインストールされているか確認してください")
        logger.error("pip install google-generativeai")
        return False
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Gemini API接続確認ツール")
    print("=" * 50)
    
    if check_api_connection():
        print("\n✅ API接続は正常です")
        sys.exit(0)
    else:
        print("\n❌ API接続に問題があります")
        sys.exit(1)
