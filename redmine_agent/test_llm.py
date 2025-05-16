#!/usr/bin/env python3
"""
LLM機能のテストスクリプト

Redmineエージェントの各種LLM機能を単独で実行し、動作確認するためのスクリプト。
"""

import sys
import os
import json
import logging
from dotenv import load_dotenv
from pathlib import Path

# アプリケーションのパスを追加
app_path = str(Path(__file__).parent)
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# ロギングの設定
# カスタムログユーティリティを使用
try:
    from app.log_utils import setup_logging
    setup_logging(level=logging.INFO)
except ImportError:
    # log_utilsがない場合は標準設定で
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

# モジュールをインポート
try:
    from app.llm_helper import RedmineAssistant
    from app.core import RedmineAgent
except ImportError as e:
    logger.error(f"モジュールのインポート中にエラーが発生しました: {e}")
    sys.exit(1)

def main():
    # Redmine情報の読み込み
    redmine_url = os.getenv("REDMINE_URL")
    redmine_api_key = os.getenv("REDMINE_API_KEY")
    
    if not redmine_url or not redmine_api_key:
        logger.error("環境変数REDMINE_URLおよびREDMINE_API_KEYが設定されていません")
        sys.exit(1)
        
    # RedmineAgentの初期化
    redmine_agent = RedmineAgent(redmine_url=redmine_url, api_key=redmine_api_key)
    
    # RedmineAssistantの初期化
    try:
        llm_assistant = RedmineAssistant()
        logger.info("LLMアシスタントの初期化に成功しました")
    except Exception as e:
        logger.error(f"LLMアシスタントの初期化中にエラーが発生しました: {e}")
        sys.exit(1)
        
    # APIキーのテスト
    if llm_assistant._test_api_connection():
        logger.info("Gemini API接続テストに成功しました")
    else:
        logger.error("Gemini API接続テストに失敗しました")
        sys.exit(1)
        
    # テスト1: 自然言語コマンドの解析
    test_commands = [
        "今日のタスク教えて",
        "タスク123に2時間記録して内容は機能実装",
        "チケット456の進捗率を80%に更新",
        "週間レポートを見せて"
    ]
    
    print("\n--- テスト1: 自然言語コマンドの解析 ---")
    for cmd in test_commands:
        result = llm_assistant.analyze_natural_language_command(cmd)
        print(f"入力: '{cmd}'")
        print(f"解析結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print("---")
    
    # テスト2: チケット緊急度の評価
    try:
        print("\n--- テスト2: チケット緊急度の評価 ---")
        # サンプルデータの作成
        sample_issue = {
            "id": 123,
            "subject": "重要機能の実装",
            "status": {"name": "新規"},
            "priority": {"name": "高"},
            "done_ratio": 0,
            "start_date": "2025-05-10",
            "due_date": "2025-05-20",
            "description": "クライアントからの要望で急ぎの対応が必要。期日厳守。"
        }
        
        urgency = llm_assistant.evaluate_ticket_urgency(sample_issue)
        print(f"緊急度評価結果: {json.dumps(urgency, ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"チケット緊急度の評価中にエラーが発生しました: {e}")
    
    # テスト3: 次のアクションの提案
    try:
        print("\n--- テスト3: 次のアクションの提案 ---")
        actions = llm_assistant.suggest_next_actions(sample_issue)
        print(f"提案されるアクション: {json.dumps(actions, ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"次のアクションの提案中にエラーが発生しました: {e}")
    
    # テスト4: タスク優先順位付け
    try:
        print("\n--- テスト4: タスク優先順位付け ---")
        sample_tasks = [
            {
                "id": 123,
                "subject": "デザインレビュー",
                "priority": {"name": "通常"},
                "due_date": "2025-05-25",
                "done_ratio": 0
            },
            {
                "id": 124,
                "subject": "バグ修正",
                "priority": {"name": "高"},
                "due_date": "2025-05-16",
                "done_ratio": 30
            },
            {
                "id": 125,
                "subject": "ドキュメント作成",
                "priority": {"name": "低"},
                "due_date": "2025-05-30",
                "done_ratio": 80
            }
        ]
        
        prioritized = llm_assistant.prioritize_tasks(sample_tasks)
        print(f"優先順位付けされたタスク: {json.dumps(prioritized, ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"タスク優先順位付け中にエラーが発生しました: {e}")
    
    print("\nすべてのテストが完了しました")

if __name__ == "__main__":
    main()
