"""
Redmine Agentの自然言語処理支援モジュール

Gemini APIを活用して、Redmineチケットの分析や提案を行う機能を提供します。
"""

import os
import json
import logging
import time
import random
import requests
from typing import Dict, List, Any, Optional, Tuple, Union
from dotenv import load_dotenv

# 共通ロガー設定
logger = logging.getLogger(__name__)

# 環境変数のロード
load_dotenv()

class RedmineAssistant:
    """GeminiモデルによるRedmineチケット管理アシスタント"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初期化
        
        Args:
            api_key: GeminiのAPIキー（指定がなければ環境変数から取得）
        """
        # APIキーの設定
        if api_key:
            self.api_keys = [api_key]
            logger.info("指定されたAPIキーを使用します")
        else:
            # 複数のAPIキーをロード（ローテーション用）
            keys_to_try = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY1", "GEMINI_API_KEY2"]
            self.api_keys = []
            for key_name in keys_to_try:
                key_value = os.getenv(key_name)
                if key_value:
                    self.api_keys.append(key_value)
                    logger.info(f"環境変数 {key_name} からAPIキーをロードしました")
            
            if not self.api_keys:
                logger.warning("有効なGemini APIキーが見つかりません。デモモードで動作します")
        
        self.current_key_index = 0
        self.api_key = self.api_keys[0] if self.api_keys else None
        
        # APIエンドポイントとモデル設定
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash"  # 高速なモデルを使用
        
        # リトライ設定
        self.max_retries = 3
        self.retry_delay = 2  # 秒
        
        # API接続テスト
        if self.api_key:
            self._test_api_connection()
    
    def _test_api_connection(self) -> bool:
        """API接続テスト"""
        if not self.api_key:
            return False
        
        try:
            logger.info("Gemini API接続テスト実行中...")
            response = requests.post(
                f"{self.base_url}/{self.model}:generateContent?key={self.api_key}",
                json={"contents": [{"parts": [{"text": "Test"}]}]},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Gemini API接続テスト成功")
                return True
            else:
                logger.error(f"Gemini API接続テスト失敗: ステータス {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Gemini API接続テスト中に例外発生: {str(e)}")
            return False
    
    def _rotate_api_key(self) -> bool:
        """次のAPIキーに切り替え"""
        if len(self.api_keys) <= 1:
            return False
            
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.api_key = self.api_keys[self.current_key_index]
        logger.info(f"APIキーをローテーション: インデックス {self.current_key_index} に切り替え")
        return True
    
    def _make_api_request(self, prompt: str, temperature: float = 0.7) -> Optional[Dict[str, Any]]:
        """Gemini APIリクエスト実行（リトライロジック含む）"""
        if not self.api_key:
            logger.warning("APIキーがないため、デモモードでレスポンス生成")
            return {"demo": True, "text": f"APIキーがないためデモレスポンス: {prompt[:30]}..."}
            
        retries = 0
        while retries < self.max_retries:
            try:
                logger.info(f"Gemini APIリクエスト実行 (試行 {retries+1}/{self.max_retries})")
                
                response = requests.post(
                    f"{self.base_url}/{self.model}:generateContent?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": temperature}
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [401, 403, 429]:
                    # 認証エラーやレート制限の場合はAPIキーをローテーション
                    logger.warning(f"APIエラー ({response.status_code}). キーローテーション試行...")
                    if self._rotate_api_key():
                        # キーを切り替えて少し待機
                        time.sleep(self.retry_delay)
                    else:
                        # ローテーションできなければ通常の再試行
                        logger.error("APIキーのローテーションができません")
                        retries += 1
                        time.sleep(self.retry_delay * (2 ** retries))
                else:
                    # その他のエラーは通常の再試行
                    logger.error(f"APIエラー: {response.status_code} - {response.text[:200]}")
                    retries += 1
                    time.sleep(self.retry_delay * (2 ** retries))
                    
            except Exception as e:
                logger.error(f"APIリクエスト中に例外発生: {str(e)}")
                retries += 1
                time.sleep(self.retry_delay * (2 ** retries))
        
        logger.error(f"Gemini APIリクエストが{self.max_retries}回の再試行後に失敗")
        return None
    
    def extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """Gemini APIレスポンスからテキスト部分を抽出"""
        try:
            if response and "candidates" in response:
                return response["candidates"][0]["content"]["parts"][0]["text"]
            elif response and "demo" in response:
                return response["text"]
            else:
                return "レスポンスからテキストを抽出できませんでした"
        except (KeyError, IndexError) as e:
            logger.error(f"レスポンス抽出中にエラー: {str(e)}")
            return "レスポンス構造エラー"
    
    def suggest_next_actions(self, issue_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        チケットに関する次のアクションを提案
        
        Args:
            issue_data: Redmineから取得したチケット情報
            
        Returns:
            提案アクションのリスト
        """
        prompt = f"""
        以下のRedmineチケット情報から、次に取るべきアクション（最大5つ）を提案してください。
        
        チケット情報:
        件名: {issue_data.get("subject", "情報なし")}
        ステータス: {issue_data.get("status", {}).get("name", "情報なし")}
        進捗率: {issue_data.get("done_ratio", 0)}%
        優先度: {issue_data.get("priority", {}).get("name", "情報なし")}
        担当者: {issue_data.get("assigned_to", {}).get("name", "未割当")}
        開始日: {issue_data.get("start_date", "未設定")}
        期日: {issue_data.get("due_date", "未設定")}
        
        説明:
        {issue_data.get("description", "説明なし")}
        
        以下のJSON形式で応答してください:
        [
          {{
            "title": "アクションのタイトル",
            "description": "具体的な説明",
            "priority": "高" | "中" | "低",
            "estimated_hours": 推定時間（数値、省略可）
          }}
        ]
        """
        
        response = self._make_api_request(prompt, temperature=0.3)
        if not response:
            return self._generate_fallback_suggestions(issue_data)
            
        try:
            text = self.extract_text_from_response(response)
            
            # JSONブロックを抽出
            import re
            json_match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = text
                
            suggestions = json.loads(json_str)
            logger.info(f"{len(suggestions)}件の次アクション提案を生成しました")
            return suggestions
            
        except Exception as e:
            logger.error(f"提案生成中にエラー: {str(e)}")
            return self._generate_fallback_suggestions(issue_data)
    
    def _generate_fallback_suggestions(self, issue_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """APIエラー時のフォールバック提案"""
        status = issue_data.get("status", {}).get("name", "").lower()
        done_ratio = issue_data.get("done_ratio", 0)
        
        suggestions = []
        
        # ステータスに基づく提案
        if "新規" in status:
            suggestions.append({
                "title": "要件の詳細分析",
                "description": "チケットの要件を詳細に分析し、必要な作業を明確にする",
                "priority": "高"
            })
        elif "進行中" in status:
            if done_ratio < 50:
                suggestions.append({
                    "title": "進捗状況の更新",
                    "description": "現在の進捗状況を更新し、残りの作業を確認する",
                    "priority": "中"
                })
            else:
                suggestions.append({
                    "title": "テスト計画の作成",
                    "description": "実装完了に向けてテスト計画を作成する",
                    "priority": "中"
                })
                
        # 基本的な提案を追加
        suggestions.extend([
            {
                "title": "関連資料の確認",
                "description": "チケットに関連する資料や文書を確認する",
                "priority": "中"
            },
            {
                "title": "チームメンバーとの情報共有",
                "description": "現状の進捗や課題についてチームメンバーと共有する",
                "priority": "中"
            }
        ])
        
        return suggestions[:5]  # 最大5つまで

    def evaluate_ticket_urgency(self, issue_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        チケットの緊急度を評価
        
        Args:
            issue_data: Redmineから取得したチケット情報
            
        Returns:
            緊急度評価結果
        """
        import datetime
        
        today = datetime.date.today().isoformat()
        due_date = issue_data.get("due_date", "")
        priority_name = issue_data.get("priority", {}).get("name", "中")
        
        prompt = f"""
        以下のRedmineチケット情報から、このチケットの緊急度を評価してください。
        
        チケット情報:
        件名: {issue_data.get("subject", "情報なし")}
        ステータス: {issue_data.get("status", {}).get("name", "情報なし")}
        進捗率: {issue_data.get("done_ratio", 0)}%
        優先度: {priority_name}
        開始日: {issue_data.get("start_date", "未設定")}
        期日: {due_date}
        今日の日付: {today}
        
        説明:
        {issue_data.get("description", "説明なし")}
        
        以下のJSON形式で応答してください:
        {{
          "urgency_score": 1から10の評価スコア（1:低緊急 ～ 10:最緊急）,
          "is_blocking": 他の作業をブロックしている可能性（trueまたはfalse）,
          "reason": "緊急度評価の理由",
          "recommended_action": "推奨されるアクション"
        }}
        """
        
        response = self._make_api_request(prompt, temperature=0.2)
        if not response:
            # 応答がない場合は基本的な評価を行う
            days_until_due = -1
            if due_date:
                try:
                    due_date_obj = datetime.date.fromisoformat(due_date)
                    days_until_due = (due_date_obj - datetime.date.today()).days
                except:
                    pass
            
            # 基本ロジックによる評価
            urgency_score = 5  # デフォルト
            if days_until_due < 0:
                urgency_score = 9  # 期限切れ
            elif days_until_due == 0:
                urgency_score = 8  # 今日が期限
            elif days_until_due < 3:
                urgency_score = 7  # 期限が近い
            
            # 優先度による調整
            priority_boost = {
                "低": -2,
                "通常": 0,
                "高": +2,
                "急いで": +3,
                "今すぐ": +4
            }.get(priority_name, 0)
            
            urgency_score = max(1, min(10, urgency_score + priority_boost))
            
            return {
                "urgency_score": urgency_score,
                "is_blocking": urgency_score >= 8,
                "reason": "期限と優先度に基づく基本評価",
                "recommended_action": "チケットを確認し、適切なアクションを取ってください" 
            }
        
        try:
            text = self.extract_text_from_response(response)
            result = json.loads(text)
            logger.info(f"チケット緊急度評価を生成: スコア={result.get('urgency_score', 'なし')}")
            return result
            
        except Exception as e:
            logger.error(f"緊急度評価中にエラー: {str(e)}")
            return {
                "urgency_score": 5,
                "is_blocking": False,
                "reason": "基本評価 (APIエラーのため)",
                "recommended_action": "チケットの詳細を確認してください" 
            }

    def prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        タスクリストの最適な優先順位付け
        
        Args:
            tasks: タスクのリスト
            
        Returns:
            優先順位付けされたタスクのリスト
        """
        if not tasks:
            return []
            
        tasks_str = json.dumps(tasks, ensure_ascii=False)
        
        prompt = f"""
        以下のタスクリストを、最適な優先順位で並べ替えてください。
        重要度、緊急度、依存関係、作業効率を考慮してください。
        
        タスク:
        {tasks_str}
        
        以下のJSON形式で、優先順に並べ替えたタスクリストを返してください。
        各タスクに「priority_reason」フィールドを追加して、優先度の理由を説明してください。
        """
        
        response = self._make_api_request(prompt, temperature=0.2)
        if not response:
            # 基本的な優先順位付けを行う
            # 期限、優先度、進捗率に基づいてソート
            try:
                import datetime
                today = datetime.date.today()
                
                # 基本スコアの計算
                for task in tasks:
                    score = 0
                    
                    # 期限に基づくスコア
                    due_date = task.get("due_date")
                    if due_date:
                        try:
                            due_date_obj = datetime.date.fromisoformat(due_date)
                            days_until_due = (due_date_obj - today).days
                            if days_until_due < 0:
                                score += 100  # 期限切れ
                            elif days_until_due == 0:
                                score += 90   # 今日期限
                            elif days_until_due <= 3:
                                score += 80   # 3日以内
                            elif days_until_due <= 7:
                                score += 70   # 1週間以内
                        except:
                            pass
                    
                    # 優先度に基づくスコア
                    priority = task.get("priority", {}).get("name", "")
                    priority_score = {
                        "低": 0,
                        "通常": 10,
                        "高": 20,
                        "急いで": 30,
                        "今すぐ": 40
                    }.get(priority, 10)
                    score += priority_score
                    
                    # 進捗率に基づくスコア（進捗率が高いものを優先）
                    done_ratio = task.get("done_ratio", 0)
                    if done_ratio >= 80:
                        score += 15  # ほぼ完了したものを優先
                    
                    # スコアを保存
                    task["_priority_score"] = score
                    task["priority_reason"] = "期限、優先度、進捗率に基づく自動評価"
                
                # スコアでソート
                sorted_tasks = sorted(tasks, key=lambda t: t.get("_priority_score", 0), reverse=True)
                
                # 一時フィールドを削除
                for task in sorted_tasks:
                    if "_priority_score" in task:
                        del task["_priority_score"]
                
                return sorted_tasks
                
            except Exception as e:
                logger.error(f"基本優先順位付けでエラー: {str(e)}")
                # エラー時は元のリストを返す
                for task in tasks:
                    task["priority_reason"] = "元の順序を維持（処理エラー）"
                return tasks
        
        try:
            text = self.extract_text_from_response(response)
            # "```json" などのマークダウン記法を除去
            import re
            cleaned_text = re.sub(r'```(?:json)?\n?|\n?```', '', text).strip()
            prioritized_tasks = json.loads(cleaned_text)
            logger.info(f"{len(prioritized_tasks)}件のタスクを優先順位付けしました")
            return prioritized_tasks
            
        except Exception as e:
            logger.error(f"タスク優先順位付け中にエラー: {str(e)}")
            # エラー時は元のリストを返す
            for task in tasks:
                task["priority_reason"] = "元の順序を維持（処理エラー）"
            return tasks

    def generate_daily_summary(self, completed_tasks: List[Dict[str, Any]], time_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        1日の作業サマリーを生成
        
        Args:
            completed_tasks: 完了したタスクのリスト
            time_entries: 作業時間記録のリスト
            
        Returns:
            1日のサマリー
        """
        completed_str = json.dumps(completed_tasks, ensure_ascii=False)
        time_entries_str = json.dumps(time_entries, ensure_ascii=False)
        
        prompt = f"""
        以下の完了タスクと作業時間記録から、今日の作業サマリーを生成してください。
        
        完了タスク:
        {completed_str}
        
        作業時間記録:
        {time_entries_str}
        
        以下のJSON形式で応答してください:
        {{
          "summary": "全体のサマリー（最大200文字）",
          "achievements": ["主な成果のリスト（最大3つ）"],
          "focus_areas": ["今日の主な活動分野"],
          "productivity_score": 1から10の生産性スコア,
          "recommendations": ["明日に向けた提案（最大2つ）"]
        }}
        """
        
        response = self._make_api_request(prompt)
        if not response:
            # 基本的なサマリーを生成
            total_hours = sum(entry.get("hours", 0) for entry in time_entries)
            
            # タスク名のみを抽出
            task_names = [task.get("subject", "名称不明") for task in completed_tasks]
            
            return {
                "summary": f"今日は{len(completed_tasks)}件のタスクを完了し、計{total_hours}時間の作業を記録しました。",
                "achievements": task_names[:3],
                "focus_areas": ["定型作業"],
                "productivity_score": 5,
                "recommendations": ["明日もオープンタスクに取り組みましょう"]
            }
        
        try:
            text = self.extract_text_from_response(response)
            # "```json" などのマークダウン記法を除去
            import re
            cleaned_text = re.sub(r'```(?:json)?\n?|\n?```', '', text).strip()
            summary_data = json.loads(cleaned_text)
            logger.info(f"日次サマリー生成完了: 生産性スコア={summary_data.get('productivity_score', 'なし')}")
            return summary_data
            
        except Exception as e:
            logger.error(f"日次サマリー生成中にエラー: {str(e)}")
            # 基本的なサマリーを返す
            total_hours = sum(entry.get("hours", 0) for entry in time_entries)
            return {
                "summary": f"今日は{len(completed_tasks)}件のタスクを完了し、計{total_hours}時間の作業を記録しました。",
                "achievements": [task.get("subject", "名称不明") for task in completed_tasks[:3]],
                "focus_areas": ["定型作業"],                "productivity_score": 5,
                "recommendations": ["明日もオープンタスクに取り組みましょう"]
            }
    
    def analyze_natural_language_command(self, text: str) -> Dict[str, Any]:
        """
        自然言語コマンドを分析し、構造化された形式に変換
        
        Args:
            text: 自然言語のテキスト
            
        Returns:
            構造化されたコマンド情報
        """
        # メッセージを前処理（長すぎる場合は切り詰める）
        if len(text) > 500:
            original_length = len(text)
            text = text[:497] + "..."
            logger.warning(f"メッセージが長すぎるため切り詰めました: {original_length}文字→500文字")
        
        prompt = f"""
        以下の自然言語テキストを解析し、Redmineチケット管理システムで実行可能なコマンドに変換してください。
        
        テキスト: "{text}"
        
        以下の形式で応答してください:
        {{
          "command_type": "task_list" | "log_time" | "update_status" | "update_progress" | "summary" | "optimize" | "report" | "search" | "help" | "unknown",
          "ticket_id": チケットID（該当する場合、数値）,
          "hours": 作業時間（時間単位、該当する場合、数値）,
          "status_id": ステータスID（該当する場合、数値）,
          "done_ratio": 進捗率（該当する場合、0-100の数値）,
          "comment": "コメント内容（該当する場合）",
          "search_query": "検索クエリ（該当する場合）",
          "report_type": "レポートタイプ (today/week)（該当する場合）",
          "days": 日数（該当する場合、数値）,
          "confidence": 解釈の信頼度（0.0-1.0）
        }}
        
        例えば、「タスク#123に2時間記録して、内容は打ち合わせ」は以下のように解析されます:
        {{
          "command_type": "log_time",
          "ticket_id": 123,
          "hours": 2,
          "comment": "打ち合わせ",
          "confidence": 0.95
        }}
        """
        
        response = self._make_api_request(prompt, temperature=0.1)
        if not response:
            # 基本的な解析を試みる
            import re
            
            result = {
                "command_type": "unknown",
                "confidence": 0.5
            }
            
            # 今日/本日のタスクパターン
            if re.search(r'(今日|本日).*(タスク|予定|やること)', text):
                result["command_type"] = "task_list"
                result["confidence"] = 0.8
                
            # 作業時間記録パターン
            time_log_match = re.search(r'(タスク|チケット)?#?(\d+).*?(\d+[\.,]?\d*).*?(時間|h|hours)', text)
            if time_log_match:
                result["command_type"] = "log_time"
                result["ticket_id"] = int(time_log_match.group(2))
                result["hours"] = float(time_log_match.group(3).replace(',', '.'))
                
                # コメント抽出
                comment_match = re.search(r'内容[はが]?[：:]?\s*「?([^」]+)」?', text) or re.search(r'コメント[：:]?\s*「?([^」]+)」?', text)
                if comment_match:
                    result["comment"] = comment_match.group(1)
                result["confidence"] = 0.75
                
            # 進捗率更新パターン
            progress_match = re.search(r'(タスク|チケット)?#?(\d+).*?(\d+).*?(%|パーセント|進捗率)', text)
            if progress_match:
                result["command_type"] = "update_progress"
                result["ticket_id"] = int(progress_match.group(2))
                result["done_ratio"] = int(progress_match.group(3))
                result["confidence"] = 0.75
            
            # サマリーパターン
            summary_match = re.search(r'(タスク|チケット)#?(\d+).*(詳細|サマリー|要約|内容)', text)
            if summary_match:
                result["command_type"] = "summary"
                result["ticket_id"] = int(summary_match.group(2))
                result["confidence"] = 0.8
                
            # レポートパターン
            if re.search(r'(レポート|報告).*(今日|本日)', text) or "今日の作業" in text:
                result["command_type"] = "report"
                result["report_type"] = "today"
                result["confidence"] = 0.8
            elif re.search(r'(レポート|報告).*(週間|今週|先週)', text):
                result["command_type"] = "report"
                result["report_type"] = "week"
                result["confidence"] = 0.8
                
            # 最適化パターン
            if re.search(r'(最適化|効率化|優先順位|優先度).*(提案|教えて)', text):
                result["command_type"] = "optimize"
                result["confidence"] = 0.8
                
            # ヘルプパターン
            if "ヘルプ" in text or "使い方" in text or "help" in text.lower() or "コマンド" in text:
                result["command_type"] = "help"
                result["confidence"] = 0.9
                
            return result
        
        try:
            text = self.extract_text_from_response(response)
            
            # "```json" などのマークダウン記法を除去
            import re
            cleaned_text = re.sub(r'```(?:json)?\n?|\n?```', '', text).strip()
            
            # JSONのトリミングと修正（JSONの外側に余計なテキストがある場合の対策）
            json_start = cleaned_text.find('{')
            json_end = cleaned_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                cleaned_text = cleaned_text[json_start:json_end]
            
            command_data = json.loads(cleaned_text)
            
            # 信頼度が低すぎる場合は警告
            confidence = command_data.get('confidence', 0)
            if confidence < 0.4:
                logger.warning(f"コマンド解析の信頼度が低すぎます: {confidence}")
            
            logger.info(f"コマンド解析: type={command_data.get('command_type')}, confidence={confidence}")
            return command_data
            
        except Exception as e:
            logger.error(f"自然言語コマンド解析中にエラー: {str(e)}")
            return {
                "command_type": "unknown",
                "confidence": 0.3,
                "error": str(e)
            }

    def suggest_task_optimization(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        タスク最適化の提案を生成
        
        Args:
            tasks: タスクのリスト
            
        Returns:
            最適化提案
        """
        if not tasks:
            return {
                "summary": "タスクがないため、最適化提案はありません。",
                "suggestions": []
            }
            
        tasks_str = json.dumps(tasks, ensure_ascii=False)
        
        prompt = f"""
        以下のタスクリストを分析し、タスク管理の効率化のための提案を行ってください。
        重要度、緊急度、類似性、時間管理の視点から分析してください。
        
        タスク:
        {tasks_str}
        
        以下のJSON形式で応答してください:
        {{
          "summary": "全体の分析概要と改善ポイント（最大300文字）",
          "similar_tasks": [{{
            "task_ids": [類似タスクのIDリスト],
            "reason": "類似理由",
            "optimization": "最適化提案"
          }}],
          "priority_changes": [{{
            "task_id": タスクID,
            "current_priority": "現在の優先度",
            "suggested_priority": "提案優先度",
            "reason": "変更理由"
          }}],
          "time_management": [{{
            "task_id": タスクID,
            "suggestion": "時間管理の提案",
            "reason": "提案理由"
          }}],
          "general_suggestions": ["全般的な提案（最大3つ）"]
        }}
        """
        
        response = self._make_api_request(prompt)
        if not response:
            # 基本的な提案を生成
            return {
                "summary": "タスクの効率的な管理のために、期限が近いものから優先的に取り組み、類似するタスクはまとめて実施することをお勧めします。",
                "similar_tasks": [],
                "priority_changes": [],
                "time_management": [],
                "general_suggestions": [
                    "優先度の高いタスクから順に着手してください",
                    "時間の見積もりを設定し、実際の作業時間と比較することで精度を高めてください",
                    "継続的にタスクの進捗を更新し、チームと共有してください"
                ]
            }
        
        try:
            text = self.extract_text_from_response(response)
            # "```json" などのマークダウン記法を除去
            import re
            cleaned_text = re.sub(r'```(?:json)?\n?|\n?```', '', text).strip()
            optimization_data = json.loads(cleaned_text)
            logger.info(f"タスク最適化提案生成完了: {len(optimization_data.get('general_suggestions', []))}件の一般提案")
            return optimization_data
            
        except Exception as e:
            logger.error(f"タスク最適化提案生成中にエラー: {str(e)}")
            # 基本的な提案を返す
            return {
                "summary": "タスクの効率的な管理のために、期限が近いものから優先的に取り組み、類似するタスクはまとめて実施することをお勧めします。",
                "similar_tasks": [],
                "priority_changes": [],
                "time_management": [],
                "general_suggestions": [
                    "優先度の高いタスクから順に着手してください",
                    "時間の見積もりを設定し、実際の作業時間と比較することで精度を高めてください",
                    "継続的にタスクの進捗を更新し、チームと共有してください"
                ]
            }
