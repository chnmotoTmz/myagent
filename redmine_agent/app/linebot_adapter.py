"""
LINE Bot アダプター

LINEからのメッセージを解釈し、Redmine Agentの機能を呼び出すアダプター。
簡易版：LINE APIに依存せずにメッセージの処理ロジックのみを実装
"""

import os
import re
import json
import logging
import datetime
import requests
from typing import Dict, List, Any, Optional, Tuple

from .core import RedmineAgent
from .nlp_helper import extract_command_intent
import importlib.util

# LLM利用可能フラグをチェック
LLM_READY = False
if importlib.util.find_spec("google.generativeai") is not None:
    LLM_READY = True

logger = logging.getLogger(__name__)

class LineBotAdapter:
    """LINE Botアダプター（簡易版）"""
    
    def __init__(self, line_token: str, redmine_agent: RedmineAgent):
        """
        初期化
        
        Args:
            line_token: LINE Bot API Token
            redmine_agent: Redmineエージェントインスタンス
        """
        self.line_token = line_token
        self.agent = redmine_agent
        self.llm_assistant = None
        
        # LLM機能が利用可能であればアシスタントを初期化
        if LLM_READY:
            try:
                # 動的にインポート
                from .llm_helper import RedmineAssistant
                self.llm_assistant = RedmineAssistant()
                logger.info("LLMアシスタントを初期化しました")
            except Exception as e:
                logger.error(f"LLMアシスタント初期化中にエラーが発生しました: {str(e)}")
                
        self.commands = {
            "today": self._handle_today_command,
            "tasks": self._handle_tasks_command,
            "log": self._handle_log_command,
            "status": self._handle_status_command,
            "update": self._handle_update_command,
            "summary": self._handle_summary_command,
            "report": self._handle_report_command,
            "optimize": self._handle_optimize_command,
            "mode": self._handle_mode_command,
            "help": self._handle_help_command,
        }
    def handle_message(self, message_text: str, user_id: str) -> str:
        """
        メッセージを処理
        
        Args:
            message_text: 受け取ったメッセージテキスト
            user_id: ユーザーID
            
        Returns:
            応答メッセージ
        """
        try:
            # コマンド形式の解析 (@ もコマンドプレフィックスとして扱う)
            if message_text.startswith('/') or message_text.startswith('@'):
                prefix_length = 1
                command_char = message_text[0]
                
                content_after_prefix = message_text[prefix_length:].strip()
                parts = content_after_prefix.split(' ', 1)
                command_name = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""

                if command_char == '/' and command_name in self.commands:
                    return self.commands[command_name](args, user_id)
                elif command_char == '@':
                    # Future: Implement @command handling if needed
                    return f"アットマークコマンド「{command_name}」は現在サポートされていません。"
                else:
                    # This case should ideally not be reached if logic is sound
                    return "未知のコマンド形式です。 /help で確認してください。"

            # 特定のフレーズを直接処理
            if message_text == "本番にしたい":
                return self._handle_mode_command("prod", user_id)
            elif message_text == "開発モードにして" or message_text == "開発にしたい":
                return self._handle_mode_command("dev", user_id)
                
            # LLMによる自然言語解析を試行
            if self.llm_assistant:
                try:
                    logger.info("LLMによるメッセージ解析を実行します")
                    command_data = self.llm_assistant.analyze_natural_language_command(message_text)
                    confidence = command_data.get("confidence", 0)
                    command_type = command_data.get("command_type", "unknown")
                    
                    # 高信頼度で特定のコマンドタイプ（"comment"以外）と判断された場合
                    if confidence >= 0.7 and command_type != "unknown" and command_type != "comment":
                        logger.info(f"LLMがコマンド '{command_type}' を検出しました (信頼度: {confidence:.2f})")
                        if command_type == "task_list":
                            return self._handle_today_command("", user_id)
                        elif command_type == "log_time":
                            ticket_id = command_data.get("ticket_id")
                            hours = command_data.get("hours")
                            comment = command_data.get("comment", "")
                            if ticket_id and hours:
                                params = f"{ticket_id} {hours} {comment}"
                                return self._handle_log_command(params, user_id)
                            else:
                                logger.warning(f"LLM parsed log_time but missing ticket_id or hours: {command_data}")
                                # Fall through to ticket creation or a more specific error
                        elif command_type == "update_status":
                            ticket_id = command_data.get("ticket_id")
                            status_id = command_data.get("status_id") # Ensure LLM returns this
                            if ticket_id and status_id:
                                params = f"{ticket_id} {status_id}"
                                return self._handle_status_command(params, user_id)
                            else:
                                logger.warning(f"LLM parsed update_status but missing ticket_id or status_id: {command_data}")
                                # Fall through to ticket creation
                        elif command_type == "search":
                            query = command_data.get("search_query", "")
                            return f"「{query}」による検索機能は現在開発中です。"
                        elif command_type == "help":
                            return self._handle_help_command("", user_id)
                        # If LLM handled it, return. Otherwise, it might be a comment or low confidence.
                        # For other specific commands handled by LLM, ensure they return here.
                        # If not, it will fall through.
                    
                    # LLMが "comment" と判断したか、信頼度が低い場合はチケット作成へ
                    if command_type == "comment" or confidence < 0.7:
                         logger.info(f"LLM解析結果がコメントまたは低信頼度 ({command_type}, {confidence:.2f})。チケット作成を試みます。")
                    # No explicit return here, fall through to ticket creation logic

                except Exception as e:
                    logger.error(f"LLMによるメッセージ解析中にエラーが発生しました: {str(e)}")
                    # エラー時は従来のロジック (チケット作成) にフォールバック
            
            # コマンドでもなく、LLMが高信頼度で特定コマンドと解釈しなかった場合、
            # またはLLMが無効/エラーの場合、新しいチケットとして登録
            logger.info(f"コマンド形式ではない、またはLLMが特定コマンドと解釈しなかったため、新しいチケットとして登録処理を開始します: {message_text[:50]}...")
            
            default_project_id_str = os.getenv("DEFAULT_PROJECT_ID")
            default_tracker_id_str = os.getenv("DEFAULT_TRACKER_ID")

            if not default_project_id_str:
                logger.error("環境変数 DEFAULT_PROJECT_ID が設定されていません。")
                return "チケット作成に必要なプロジェクトIDが設定されていません。管理者に連絡してください。"
            
            try:
                project_id = int(default_project_id_str)
                tracker_id = int(default_tracker_id_str) if default_tracker_id_str and default_tracker_id_str.isdigit() else None
            except ValueError:
                logger.error(f"環境変数 DEFAULT_PROJECT_ID ('{default_project_id_str}') または DEFAULT_TRACKER_ID ('{default_tracker_id_str}') の値が不正です。")
                return "チケット作成に必要なプロジェクトIDまたはトラッカーIDの設定値が不正です。管理者に連絡してください。"

            # メッセージ全体を題名としてチケット作成
            # 題名と説明を分ける場合は、ここでロジックを調整
            subject = message_text 
            description = f"LINEユーザー ({user_id}) からの投稿です。\n\n{message_text}" # 説明にもメッセージ本文を含める

            created_issue = self.agent.create_issue(
                project_id=project_id,
                subject=subject,
                description=description,
                tracker_id=tracker_id
            )

            if created_issue and created_issue.get("id"):
                return f"新しいチケット #{created_issue.get('id')} を作成しました: 「{subject[:30]}...」"
            else:
                return "チケットの作成に失敗しました。Redmineの設定やAPIキーを確認するか、システム管理者に連絡してください。"
        
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            return f"メッセージ処理中に予期せぬエラーが発生しました: {str(e)}"
    
    def _handle_today_command(self, args: str, user_id: str) -> str:
        """今日のタスクを表示"""
        tasks = self.agent.get_daily_tasks()
        return self.agent.format_morning_report(tasks)
    
    def _handle_tasks_command(self, args: str, user_id: str) -> str:
        """今後のタスクを表示"""
        days = 7  # デフォルト
        
        # 日数指定があれば解析
        if args:
            match = re.search(r'(\d+)日', args)
            if match:
                try:
                    days = int(match.group(1))
                except ValueError:
                    pass
        
        tasks = self.agent.get_upcoming_tasks(days=days)
        
        if not tasks:
            return f"今後{days}日間の予定タスクはありません。"
        
        result = f"今後{days}日間の予定タスク:\n\n"
        
        for i, task in enumerate(tasks, 1):
            subject = task.get("subject", "無題")
            due_date = task.get("due_date", "期限なし")
            priority = task.get("priority", {}).get("name", "中")
            
            result += f"{i}. {subject} (期限:{due_date}, 優先度:{priority})\n"
        
        return result
    
    def _handle_log_command(self, args: str, user_id: str) -> str:
        """作業時間を記録"""
        # 構文: <チケットID> <時間> <コメント>
        parts = args.split(' ', 2)
        
        if len(parts) < 2:
            return "使用方法: /log <チケットID> <時間> <コメント>"
        
        try:
            issue_id = int(parts[0])
            hours = float(parts[1])
            comments = parts[2] if len(parts) > 2 else ""
            
            success = self.agent.log_time_entry(issue_id, hours, comments)
            
            if success:
                # 追加の情報を取得
                issue_info = {}
                response = requests.get(
                    f"{self.agent.redmine_url}/issues/{issue_id}.json",
                    headers=self.agent.headers
                )
                if response.status_code == 200:
                    issue_info = response.json().get("issue", {})
                
                subject = issue_info.get("subject", f"チケット#{issue_id}")
                
                # 今日の作業時間を取得
                today = datetime.date.today().isoformat()
                time_entries = self.agent.get_time_entries(
                    issue_id=issue_id, 
                    from_date=today, 
                    to_date=today
                )
                total_hours_today = sum(entry["hours"] for entry in time_entries)
                
                return (
                    f"{subject} に {hours}時間の作業を記録しました。\n"
                    f"コメント: {comments}\n\n"
                    f"今日の合計作業時間: {total_hours_today}時間"
                )
            else:
                return "作業時間の記録に失敗しました。"
        
        except (ValueError, IndexError) as e:
            return f"入力形式が正しくありません: {str(e)}"
    
    def _handle_status_command(self, args: str, user_id: str) -> str:
        """チケットのステータスを更新"""
        # 構文: <チケットID> <ステータスID> [コメント]
        parts = args.split(' ', 2)
        
        if len(parts) < 2:
            return "使用方法: /status <チケットID> <ステータスID> [コメント]"
        
        try:
            issue_id = int(parts[0])
            status_id = int(parts[1])
            notes = parts[2] if len(parts) > 2 else None
            
            success = self.agent.update_issue_status(issue_id, status_id, notes)
            
            if success:
                return f"チケット#{issue_id}のステータスを {status_id} に更新しました。"
            else:
                return "ステータスの更新に失敗しました。"
        
        except (ValueError, IndexError) as e:
            return f"入力形式が正しくありません: {str(e)}"
    
    def _handle_update_command(self, args: str, user_id: str) -> str:
        """チケットの進捗率を更新"""
        # 構文: <チケットID> <進捗率> [コメント]
        parts = args.split(' ', 2)
        
        if len(parts) < 2:
            return "使用方法: /update <チケットID> <進捗率> [コメント]"
        
        try:
            issue_id = int(parts[0])
            done_ratio = int(parts[1])
            notes = parts[2] if len(parts) > 2 else None
            
            if done_ratio < 0 or done_ratio > 100:
                return "進捗率は0～100の間で指定してください。"
            
            success = self.agent.update_issue_progress(issue_id, done_ratio, notes)
            
            if success:
                return f"チケット#{issue_id}の進捗率を {done_ratio}% に更新しました。"
            else:
                return "進捗率の更新に失敗しました。"
        
        except (ValueError, IndexError) as e:
            return f"入力形式が正しくありません: {str(e)}"
    
    def _handle_summary_command(self, args: str, user_id: str) -> str:
        """チケットの要約を表示"""
        # 構文: <チケットID>
        try:
            issue_id = int(args.strip())
            summary = self.agent.summarize_ticket_history(issue_id)
            
            if "error" in summary:
                return summary["error"]
            
            # 要約情報をフォーマット
            result = f"チケット #{issue_id} の要約:\n\n"
            result += f"題名: {summary['subject']}\n"
            result += f"状態: {summary['status']}\n"
            result += f"進捗: {summary['done_ratio']}%\n"
            result += f"見積時間: {summary['estimated_hours'] or '未設定'}\n"
            result += f"合計作業時間: {summary['total_time_spent']}時間\n\n"
            
            # 次のタスク
            next_tasks = self.agent.generate_next_tasks(issue_id)
            if next_tasks:
                result += "■ 推奨タスク:\n"
                for i, task in enumerate(next_tasks, 1):
                    status = "✅" if task.get("completed") else "⬜"
                    priority = task.get("priority", "中")
                    result += f"{i}. {status} {task['title']} (優先度:{priority})\n"
            
            if summary['recent_comments']:
                result += "\n■ 最近のコメント:\n"
                for comment in summary['recent_comments']:
                    date = datetime.datetime.fromisoformat(comment['date']).strftime("%m/%d")
                    text = comment['text']
                    if len(text) > 50:
                        text = text[:50] + "..."
                    result += f"- {date} ({comment['user']}): {text}\n"
            
            return result
            
        except ValueError:
            return "チケットIDを正しく指定してください。例: /summary 123"
    
    def _handle_report_command(self, args: str, user_id: str) -> str:
        """レポート生成"""
        # 構文: <レポートタイプ> [パラメータ]
        parts = args.lower().split(' ', 1)
        report_type = parts[0] if parts else "help"
        params = parts[1] if len(parts) > 1 else ""
        
        if report_type == "today":
            # 本日の作業
            today = datetime.date.today().isoformat()
            time_entries = self.agent.get_time_entries(
                from_date=today,
                to_date=today
            )
            completed_tasks = []
            
            return self.agent.format_evening_report(completed_tasks, time_entries)
            
        elif report_type == "week":
            # 週間レポート
            return self.agent.generate_weekly_summary()
        else:
            return (
                "使用可能なレポート:\n"
                "/report today - 今日の作業レポート\n"
                "/report week - 週間サマリーレポート"
            )
    
    def _handle_optimize_command(self, args: str, user_id: str) -> str:
        """タスク最適化の提案"""
        return self.agent.suggest_task_consolidation()
        
    def _handle_mode_command(self, args: str, user_id: str) -> str:
        """動作モードの切り替え (開発・本番)"""
        import os
        import requests
        from .config import get_config
        
        # 現在のモード確認
        current_debug = os.getenv("DEBUG", "True").lower() == "true"
        current_env = get_config("system.environment", "development")
        
        if not args:
            # 引数なしの場合は現在のモードを表示
            mode = "開発モード" if current_debug else "本番モード"
            return f"現在の動作モードは「{mode}」です。\n切り替えるには '/mode dev' または '/mode prod' と入力してください。"
        
        mode = args.strip().lower()
        
        # 有効なモード指定かチェック
        if mode not in ["dev", "development", "開発", "prod", "production", "本番"]:
            return "モード指定が正しくありません。'/mode dev' または '/mode prod' と入力してください。"
            
        # モード名を標準化
        api_mode = "dev" if mode in ["dev", "development", "開発"] else "prod"
        
        try:
            # APIを使用してモード変更
            # 本番環境では実際のAPIエンドポイントを呼び出す
            if current_env == "production" and not current_debug:
                # 本番環境でのAPIコール
                response = requests.post(
                    "http://localhost:8001/api/config/mode",
                    json={"mode": api_mode}
                )
                if response.status_code == 200:
                    result = response.json()
                    mode_name = "開発モード" if api_mode == "dev" else "本番モード"
                    return f"✅ システムを「{mode_name}」に設定しました。"
                else:
                    return f"❌ モード変更に失敗しました: {response.text}"
            else:
                # 開発環境または直接呼び出し
                # 組み込みの方法でモード変更
                from dotenv import set_key
                
                # 開発モードに設定
                if api_mode == "dev":
                    set_key(".env", "DEBUG", "True")
                    set_key(".env", "LOG_LEVEL", "DEBUG")
                    from .config import set_config
                    set_config("system.environment", "development")
                    set_config("system.debug_mode", True)
                    return "✅ システムを「開発モード」に設定しました。\n開発者向け機能が有効になり、より詳細なログ出力が行われます。"
                # 本番モードに設定
                else:
                    set_key(".env", "DEBUG", "False")
                    set_key(".env", "LOG_LEVEL", "INFO")
                    from .config import set_config
                    set_config("system.environment", "production")
                    set_config("system.debug_mode", False)
                    return "✅ システムを「本番モード」に設定しました。\n運用向け設定が有効になり、セキュリティが強化されます。\n\n※このモードでは開発者向け機能は無効となります。"
                    
        except Exception as e:
            logger.error(f"モード変更中にエラーが発生しました: {str(e)}")
            return f"❌ モード変更中にエラーが発生しました: {str(e)}"
              
    def _handle_help_command(self, args: str, user_id: str) -> str:
        """ヘルプ表示"""
        # LLM機能が有効かどうかを確認
        llm_status = "✅ 有効" if self.llm_assistant else "❌ 無効"
        
        base_help = (
            "【使用可能なコマンド】\n\n"
            "/today - 本日のタスク一覧\n"
            "/tasks [日数] - 今後のタスク一覧\n"
            "/log <チケットID> <時間> <コメント> - 作業時間を記録\n"
            "/status <チケットID> <ステータスID> [コメント] - ステータスを更新\n"
            "/update <チケットID> <進捗率> [コメント] - 進捗率を更新\n"
            "/summary <チケットID> - チケットの要約を表示\n"
            "/report today - 今日の作業レポート\n"
            "/report week - 週間サマリーレポート\n"
            "/optimize - タスク効率化の提案\n"
            "/mode [dev|prod] - 動作モードの切り替え\n"
            "/help - このヘルプを表示\n\n"
        )
        
        if self.llm_assistant:
            # LLMが有効な場合の拡張ヘルプ
            return base_help + (
                "【AI自然言語機能】\n"
                "自然な日本語での指示が可能です。例:\n"
                "「今日予定されているタスクを教えて」\n"
                "「チケット135に2時間記録して、内容は顧客打ち合わせ」\n"
                "「タスク227の進捗率を80%に更新して」\n"
                "「タスクの優先順位を最適化して」\n"
                "「チケット412の詳細を教えて」\n\n"
                "LLM支援機能ステータス: " + llm_status
            )
        else:
            # LLMが無効な場合の基本ヘルプ
            return base_help + (
                "【基本的な自然言語機能】\n"
                "簡単な自然言語での指示も可能です。例:\n"
                "「今日のタスク教えて」\n"
                "「タスク135に2時間記録して、内容は打ち合わせ」\n"
                "「週間レポートを見せて」\n\n"                "LLM支援機能ステータス: " + llm_status
            )
    
    def send_message(self, user_id: str, message: str) -> bool:
        """
        LINEにメッセージを送信（簡易版：実際には送信せずにログに記録）
        
        Args:
            user_id: LINE ユーザーID
            message: 送信するメッセージ
            
        Returns:
            送信成功かどうか
        """
        from .config import get_config
        import os
        
        # 現在の動作モードを確認
        is_dev_mode = os.getenv("DEBUG", "True").lower() == "true"
        environment = get_config("system.environment", "development")
        
        try:  
            # メッセージプレフィックスを追加（開発モードの場合）
            display_message = message
            if is_dev_mode:
                display_message = f"[開発環境] {message}"
                
            # 実際のLINE APIの呼び出し
            # 本番モードでは実際にAPIを呼び出す実装に置き換え
            if environment == "production" and self.line_token != "dummy_line_token_for_development":
                logger.info(f"[PRODUCTION] Sending LINE message to {user_id}, length: {len(display_message)}")
                # TODO: 実際のLINE APIコール実装
                # from linebot import LineBotApi
                # line_bot_api = LineBotApi(self.line_token)
                # line_bot_api.push_message(user_id, TextSendMessage(text=display_message))
            
            # シミュレーションモード (開発環境または本番環境でもAPIなし)
            # Unicode文字をエスケープ処理してログに出力
            safe_message = display_message.encode('unicode_escape').decode('ascii')
            logger.info(f"[SIMULATED LINE MESSAGE] To: {user_id}, Message length: {len(display_message)}")
            # 別途デバッグログとして内容を出力（長すぎる場合は省略）
            if len(display_message) > 500:
                logger.debug(f"Message content (truncated): {display_message[:500]}...")
            else:
                logger.debug(f"Message content: {display_message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send LINE message: {e}", exc_info=True)
            return False
