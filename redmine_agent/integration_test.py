#!/usr/bin/env python3
"""
Redmineエージェント統合テスト

エージェントの主な機能を統合テストするスクリプト。
"""

import os
import sys
import json
import datetime
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

def run_core_tests():
    """コア機能のテスト"""
    from app.core import RedmineAgent
    
    print("\n----- コア機能テスト -----")
    
    # RedmineAgentの初期化
    redmine_url = os.getenv("REDMINE_URL")
    redmine_api_key = os.getenv("REDMINE_API_KEY")
    
    if not redmine_url or not redmine_api_key:
        print("❌ 環境変数REDMINE_URLおよびREDMINE_API_KEYが設定されていません")
        return False
    
    try:
        agent = RedmineAgent(redmine_url=redmine_url, api_key=redmine_api_key)
        print("✅ RedmineAgentの初期化に成功しました")
        
        # タスク取得テスト
        tasks = agent.get_daily_tasks()
        print(f"✅ 本日のタスク取得: {len(tasks)}件のタスクが見つかりました")
        
        return True
    except Exception as e:
        print(f"❌ RedmineAgent初期化に失敗: {str(e)}")
        return False

def run_llm_tests():
    """LLM機能のテスト"""
    print("\n----- LLM機能テスト -----")
    
    try:
        from app.llm_helper import RedmineAssistant
        try:
            assistant = RedmineAssistant()
            print("✅ LLMアシスタントの初期化に成功しました")
            
            # APIキーのテスト
            if assistant._test_api_connection():
                print("✅ Gemini API接続テストに成功しました")
                
                # 自然言語コマンドテスト
                test_cmd = "今日のタスク教えて"
                result = assistant.parse_natural_language_command(test_cmd)
                print(f"✅ 自然言語解析: '{test_cmd}' → {result['command_type'] if 'command_type' in result else '解析失敗'}")
                
                return True
            else:
                print("❌ Gemini API接続テストに失敗しました")
                return False
                
        except Exception as e:
            print(f"❌ LLMアシスタントの初期化に失敗: {str(e)}")
            return False
            
    except ImportError:
        print("❌ LLMヘルパーのインポートに失敗しました")
        return False

def run_line_adapter_tests():
    """LINEアダプターのテスト"""
    print("\n----- LINEアダプターテスト -----")
    
    from app.core import RedmineAgent
    
    try:
        # 必要なモジュールのインポート
        from app.linebot_adapter import LineBotAdapter
        
        # RedmineAgentの初期化
        redmine_url = os.getenv("REDMINE_URL")
        redmine_api_key = os.getenv("REDMINE_API_KEY")
        line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        
        if not (redmine_url and redmine_api_key and line_token):
            print("❌ 必要な環境変数が設定されていません")
            return False
        
        # エージェントの初期化
        agent = RedmineAgent(redmine_url=redmine_url, api_key=redmine_api_key)
        
        # LINEアダプタの初期化
        adapter = LineBotAdapter(line_token=line_token, redmine_agent=agent)
        print("✅ LINEアダプターの初期化に成功しました")
        
        # メッセージ処理テスト
        test_messages = [
            "/help",
            "今日のタスク教えて",
            "タスクの優先順位を最適化して"
        ]
        
        for msg in test_messages:
            response = adapter.handle_message(msg, "test_user")
            print(f"✅ メッセージテスト: '{msg}' → レスポンス長: {len(response)}文字")
        
        return True
    except Exception as e:
        print(f"❌ LINEアダプターテストに失敗: {str(e)}")
        return False

def run_config_tests():
    """設定モジュールのテスト"""
    print("\n----- 設定モジュールテスト -----")
    
    try:
        from app.config import get_config, set_config
        
        # 設定取得テスト
        llm_enabled = get_config("llm.enabled")
        print(f"✅ 設定取得: llm.enabled = {llm_enabled}")
        
        # 設定更新テスト
        set_config("test.integration", True)
        test_value = get_config("test.integration")
        print(f"✅ 設定更新: test.integration = {test_value}")
        
        return True
    except Exception as e:
        print(f"❌ 設定モジュールテストに失敗: {str(e)}")
        return False

def main():
    print("=" * 50)
    print("Redmineエージェント統合テスト")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    # コア機能テスト
    if run_core_tests():
        success_count += 1
    
    # LLM機能テスト
    if run_llm_tests():
        success_count += 1
    
    # LINEアダプターテスト
    if run_line_adapter_tests():
        success_count += 1
    
    # 設定モジュールテスト
    if run_config_tests():
        success_count += 1
    
    # テスト結果の表示
    print("\n" + "=" * 50)
    print(f"テスト結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("✅ 全てのテストが成功しました!")
        return 0
    else:
        print(f"❌ {total_tests - success_count}個のテストに失敗しました")
        return 1

if __name__ == "__main__":
    sys.exit(main())
