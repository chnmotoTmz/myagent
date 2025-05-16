"""
Redmineチケット管理エージェント（コア実装）

チケット管理、作業時間記録、レポート生成などの機能を提供します。
"""

import os
import requests
import datetime
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import importlib.util

# 共通ロガー設定
logger = logging.getLogger(__name__)

# LLM利用可能フラグをグローバルに定義
LLM_AVAILABLE = False

# パッケージの存在確認
if importlib.util.find_spec("google.generativeai") is not None:
    try:
        # モジュールのテスト読み込みのみ行い、実際の使用は各メソッド内で
        import google.generativeai
        LLM_AVAILABLE = True
        logger.info("Gemini LLM機能が利用可能です")
    except ImportError as e:
        logger.warning(f"google-generativeaiパッケージはあるが読み込みに失敗: {str(e)}")
else:
    logger.warning("LLM機能は無効: google-generativeaiパッケージが見つかりません")

class RedmineAgent:
    """Redmineチケット管理エージェント"""
    
    def __init__(self, redmine_url: str, api_key: str):
        """
        初期化
        
        Args:
            redmine_url: RedmineのベースURL
            api_key: RedmineのAPIキー
        """
        self.redmine_url = redmine_url
        self.api_key = api_key
        self.headers = {
            "X-Redmine-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def get_daily_tasks(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        本日予定されているタスクの取得
        
        Args:
            user_id: ユーザーID (省略時は自分のタスク)
            
        Returns:
            本日のタスク一覧
        """
        today = datetime.date.today().isoformat()
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        
        # 今日に関連するタスクを取得（より広い範囲でフィルタ）
        params = {
            "status_id": "open",
            "sort": "priority:desc,due_date:asc",
            "limit": 100
        }
        
        # OR条件で「期限切れ」「今日が期限」「期限なし」「優先度高」のいずれかに該当するタスクを取得
        # Redmine APIの制限のため、一旦すべて取得して後でフィルタリング
        
        if user_id:
            params["assigned_to_id"] = user_id
            
        response = requests.get(
            f"{self.redmine_url}/issues.json",
            headers=self.headers,
            params=params
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get daily tasks: {response.text}")
            return []
            
        data = response.json()
        issues = data.get("issues", [])
        
        # APIからの結果をさらにフィルタリング
        today_issues = []
        
        for issue in issues:
            # 以下の条件に一致するタスクを「今日のタスク」とする:
            # 1. 期限が今日のタスク
            # 2. 期限が過ぎているタスク
            # 3. 期限がなく、優先度が高いまたは急いで（ID=1,2）
            # 4. 今日開始日のタスク
            
            due_date = issue.get("due_date")
            start_date = issue.get("start_date")
            priority_id = issue.get("priority", {}).get("id", 0)
            
            if any([
                # 条件1: 今日が期限
                due_date == today,
                # 条件2: 期限切れ
                due_date and due_date < today,
                # 条件3: 優先度が高い（期限なし）
                not due_date and priority_id <= 2,
                # 条件4: 今日が開始日
                start_date == today
            ]):
                today_issues.append(issue)
        
        # 十分な量のタスクがなければ、他のオープンタスクも追加
        if len(today_issues) < 5:
            remaining_count = 5 - len(today_issues)
            # 既に追加されたタスクのIDを除外
            already_added_ids = {issue["id"] for issue in today_issues}
            for issue in issues:
                if issue["id"] not in already_added_ids:
                    today_issues.append(issue)
                    remaining_count -= 1
                    if remaining_count <= 0:
                        break
        
        return today_issues
    
    def get_upcoming_tasks(self, days: int = 7, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        今後予定されているタスクの取得
        
        Args:
            days: 何日先までのタスクを取得するか
            user_id: ユーザーID (省略時は自分のタスク)
            
        Returns:
            今後のタスク一覧
        """
        today = datetime.date.today()
        future_date = (today + datetime.timedelta(days=days)).isoformat()
        
        params = {
            "start_date": "<="+future_date,
            "due_date": ">="+today.isoformat(),
            "status_id": "open",
            "sort": "due_date:asc",
            "limit": 100
        }
        
        if user_id:
            params["assigned_to_id"] = user_id
            
        response = requests.get(
            f"{self.redmine_url}/issues.json",
            headers=self.headers,
            params=params
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get upcoming tasks: {response.text}")
            return []
            
        data = response.json()
        return data.get("issues", [])
    
    def log_time_entry(self, issue_id: int, hours: float, comments: str, spent_on: Optional[str] = None) -> bool:
        """
        作業時間の登録
        
        Args:
            issue_id: チケットID
            hours: 作業時間（時間単位）
            comments: コメント
            spent_on: 作業日 (YYYY-MM-DD形式、省略時は本日)
            
        Returns:
            成功したかどうか
        """
        if not spent_on:
            spent_on = datetime.date.today().isoformat()
            
        data = {
            "time_entry": {
                "issue_id": issue_id,
                "hours": hours,
                "comments": comments,
                "spent_on": spent_on,
                "activity_id": 4  # タスク（要確認）
            }
        }
        
        response = requests.post(
            f"{self.redmine_url}/time_entries.json",
            headers=self.headers,
            json=data
        )
        
        if response.status_code in [201, 200]:
            logger.info(f"Time entry logged successfully for issue {issue_id}")
            return True
        else:
            logger.error(f"Failed to log time entry: {response.text}")
            return False
    
    def update_issue_status(self, issue_id: int, status_id: int, notes: Optional[str] = None) -> bool:
        """
        チケットのステータス更新
        
        Args:
            issue_id: チケットID
            status_id: ステータスID
            notes: 更新時のコメント
            
        Returns:
            成功したかどうか
        """
        data = {
            "issue": {
                "status_id": status_id
            }
        }
        
        if notes:
            data["issue"]["notes"] = notes
            
        response = requests.put(
            f"{self.redmine_url}/issues/{issue_id}.json",
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            logger.info(f"Issue {issue_id} status updated to {status_id}")
            return True
        else:
            logger.error(f"Failed to update issue status: {response.text}")
            return False
    
    def update_issue_progress(self, issue_id: int, done_ratio: int, notes: Optional[str] = None) -> bool:
        """
        チケットの進捗状況更新
        
        Args:
            issue_id: チケットID
            done_ratio: 進捗率（0-100）
            notes: 更新時のコメント
            
        Returns:
            成功したかどうか
        """
        data = {
            "issue": {
                "done_ratio": done_ratio
            }
        }
        
        if notes:
            data["issue"]["notes"] = notes
            
        response = requests.put(
            f"{self.redmine_url}/issues/{issue_id}.json",
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            logger.info(f"Issue {issue_id} progress updated to {done_ratio}%")
            return True
        else:
            logger.error(f"Failed to update issue progress: {response.text}")
            return False
    
    def get_time_entries(self, issue_id: Optional[int] = None, 
                         from_date: Optional[str] = None, 
                         to_date: Optional[str] = None,
                         user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        作業時間記録の取得
        
        Args:
            issue_id: チケットID (省略可)
            from_date: 開始日 (YYYY-MM-DD形式、省略可)
            to_date: 終了日 (YYYY-MM-DD形式、省略可)
            user_id: ユーザーID (省略時は自分の作業記録)
            
        Returns:
            作業時間記録リスト
        """
        params = {
            "limit": 100
        }
        
        if issue_id:
            params["issue_id"] = issue_id
            
        if from_date:
            params["from"] = from_date
            
        if to_date:
            params["to"] = to_date
        
        if user_id:
            params["user_id"] = user_id
        
        response = requests.get(
            f"{self.redmine_url}/time_entries.json",
            headers=self.headers,
            params=params
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get time entries: {response.text}")
            return []
            
        data = response.json()
        return data.get("time_entries", [])
    
    def summarize_ticket_history(self, issue_id: int) -> Dict[str, Any]:
        """
        チケット履歴の要約
        
        Args:
            issue_id: チケットID
            
        Returns:
            チケット履歴の要約情報
        """
        # チケット情報の取得
        response = requests.get(
            f"{self.redmine_url}/issues/{issue_id}.json?include=journals",
            headers=self.headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get issue details: {response.text}")
            return {"error": f"チケット #{issue_id} の取得に失敗しました"}
            
        data = response.json()
        issue = data.get("issue", {})
        
        # 作業時間記録の取得
        time_entries = self.get_time_entries(issue_id=issue_id)
        
        # ジャーナル（コメントや変更履歴）
        journals = issue.get("journals", [])
        
        # 最近のコメントを抽出
        recent_comments = []
        for journal in journals:
            if "notes" in journal and journal["notes"].strip():
                recent_comments.append({
                    "date": journal["created_on"],
                    "user": journal.get("user", {}).get("name", "Unknown"),
                    "text": journal["notes"]
                })
        
        # 直近のコメントに絞る            recent_comments = recent_comments[-5:] if recent_comments else []
        
        # 合計作業時間の計算
        total_time_spent = sum(entry["hours"] for entry in time_entries)
        
        return {
            "id": issue.get("id"),
            "subject": issue.get("subject"),
            "status": issue.get("status", {}).get("name"),
            "done_ratio": issue.get("done_ratio", 0),
            "estimated_hours": issue.get("estimated_hours"),
            "total_time_spent": total_time_spent,
            "recent_comments": recent_comments
        }
        
    def generate_next_tasks(self, issue_id: int) -> List[Dict[str, Any]]:
        """
        次に取り組むべきタスクの提案
        
        Args:
            issue_id: チケットID
            
        Returns:
            提案されるタスクのリスト
        """
        # チケットの詳細情報を取得
        response = requests.get(
            f"{self.redmine_url}/issues/{issue_id}.json?include=children,relations",
            headers=self.headers
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get issue details: {response.text}")
            return []
            
        data = response.json()
        issue = data.get("issue", {})
        
        # LLM機能が利用可能な場合は高度な分析を行う
        global LLM_AVAILABLE
        if LLM_AVAILABLE:
            try:
                # 動的に読み込みして循環参照を避ける
                from .llm_helper import RedmineAssistant
                logger.info(f"LLMによる次のタスク提案を生成します（チケット #{issue_id}）")
                llm_assistant = RedmineAssistant()
                suggestions = llm_assistant.suggest_next_actions(issue)
                
                # RedmineAssistantからの結果をフォーマット変換
                suggested_tasks = []
                for suggestion in suggestions:
                    # APIからのレスポンスは標準化されていないため安全に取得
                    suggested_tasks.append({
                        "title": suggestion.get("title", "不明なタスク"),
                        "priority": suggestion.get("priority", "中"),
                        "completed": False,
                        "description": suggestion.get("description", ""),
                        "estimated_hours": suggestion.get("estimated_hours")
                    })
                    
                logger.info(f"LLMにより{len(suggested_tasks)}件のタスク提案が生成されました")
                return suggested_tasks[:5]  # 最大5件まで
                
            except Exception as e:
                logger.error(f"LLMによるタスク提案生成中にエラーが発生しました: {str(e)}")
                # エラー時は従来のロジックにフォールバック
                logger.info("従来のロジックにフォールバックします")
        
        # 従来のロジックによるタスク提案（LLMが利用できない場合やエラー時）
        # 提案タスクのリスト
        suggested_tasks = []
        
        # 1. チケットの種類と状態に基づく推奨タスク
        issue_type = issue.get("tracker", {}).get("name", "").lower()
        status_name = issue.get("status", {}).get("name", "")
        done_ratio = issue.get("done_ratio", 0)
        
        # ステータスと進捗に基づくタスク提案
        if status_name == "新規" and done_ratio == 0:
            suggested_tasks.append({
                "title": "要件の詳細分析",
                "priority": "高",
                "completed": False
            })
            suggested_tasks.append({
                "title": "関連資料の確認",
                "priority": "高",
                "completed": False
            })
        
        elif "進行中" in status_name:
            if done_ratio < 30:
                suggested_tasks.append({
                    "title": "実装計画の策定",
                    "priority": "高",
                    "completed": False
                })
            elif done_ratio < 70:
                suggested_tasks.append({
                    "title": "中間レビューの実施",
                    "priority": "中",
                    "completed": False
                })
            else:
                suggested_tasks.append({
                    "title": "テスト計画の策定",
                    "priority": "高",
                    "completed": False
                })
                suggested_tasks.append({
                    "title": "完了基準の確認",
                    "priority": "中",
                    "completed": False
                })
        
        # チケットの種類に基づくタスク提案
        if "バグ" in issue_type:
            suggested_tasks.append({
                "title": "再現手順の確認",
                "priority": "高",
                "completed": False
            })
            suggested_tasks.append({
                "title": "根本原因の調査",
                "priority": "高", 
                "completed": False
            })
        elif "機能" in issue_type or "開発" in issue_type:
            suggested_tasks.append({
                "title": "テストケースの作成",
                "priority": "中",
                "completed": False
            })
        
        # 2. 関連チケットの分析
        relations = issue.get("relations", [])
        has_blockers = any(r.get("relation_type") == "blocked" for r in relations)
        
        if has_blockers:
            suggested_tasks.append({
                "title": "ブロッカーの解決状況確認",
                "priority": "高",
                "completed": False
            })
        
        # 3. 子チケットの状態確認
        children = issue.get("children", [])
        if children:
            suggested_tasks.append({
                "title": "サブタスクの進捗確認",
                "priority": "中",
                "completed": False
            })
        
        # 4. チケットの説明文から特定のキーワードを抽出して提案
        description = issue.get("description", "").lower()
        if "テスト" in description or "検証" in description:
            suggested_tasks.append({
                "title": "テスト環境の準備",
                "priority": "中",
                "completed": False
            })
        
        if "リリース" in description or "デプロイ" in description:
            suggested_tasks.append({
                "title": "デプロイ計画の確認",
                "priority": "中",
                "completed": False
            })
        
        if "ドキュメント" in description or "文書" in description:
            suggested_tasks.append({
                "title": "ドキュメント作成・更新",
                "priority": "中",
                "completed": False
            })
        
        # 少なくとも3つのタスクを提案
        if len(suggested_tasks) < 3:
            default_tasks = [
                {
                    "title": "関連資料の確認",
                    "priority": "高",
                    "completed": False
                },
                {
                    "title": "実装プラン作成",
                    "priority": "高",
                    "completed": False
                },
                {
                    "title": "テスト計画の策定",
                    "priority": "中",
                    "completed": False
                }
            ]
            
            # 不足分を追加
            for task in default_tasks:
                if task["title"] not in [t["title"] for t in suggested_tasks]:
                    suggested_tasks.append(task)
                    if len(suggested_tasks) >= 3:
                        break
        
        return suggested_tasks[:5]  # 最大5件まで
    
    def create_issue(self, project_id: int, subject: str, description: Optional[str] = None,
                     tracker_id: Optional[int] = None, status_id: Optional[int] = None,
                     priority_id: Optional[int] = None, assigned_to_id: Optional[int] = None,
                     parent_issue_id: Optional[int] = None, custom_fields: Optional[List[Dict[str, Any]]] = None,
                     watcher_user_ids: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
        """
        新しいチケットを作成します。
        Redmineの標準APIでは、author_id (作成者) を直接指定することはできません。
        APIキーに紐づくユーザーが作成者になります。

        Args:
            project_id: プロジェクトID
            subject: 題名
            description: 説明 (オプション)
            tracker_id: トラッカーID (オプション)
            status_id: ステータスID (オプション)
            priority_id: 優先度ID (オプション)
            assigned_to_id: 担当者ID (オプション)
            parent_issue_id: 親チケットID (オプション)
            custom_fields: カスタムフィールド (オプション) [{"id": 1, "value": "foo"}, ...]
            watcher_user_ids: ウォッチャーのユーザーIDリスト (オプション)

        Returns:
            作成されたチケットの情報、または失敗した場合はNone
        """
        issue_data: Dict[str, Any] = {
            "project_id": project_id,
            "subject": subject,
        }
        if description:
            issue_data["description"] = description
        if tracker_id:
            issue_data["tracker_id"] = tracker_id
        if status_id:
            issue_data["status_id"] = status_id
        if priority_id:
            issue_data["priority_id"] = priority_id
        if assigned_to_id:
            issue_data["assigned_to_id"] = assigned_to_id
        if parent_issue_id:
            issue_data["parent_issue_id"] = parent_issue_id
        if custom_fields:
            issue_data["custom_fields"] = custom_fields
        if watcher_user_ids:
            issue_data["watcher_user_ids"] = watcher_user_ids

        payload = {"issue": issue_data}
        
        response = requests.post(
            f"{self.redmine_url}/issues.json",
            headers=self.headers,
            json=payload
        )

        if response.status_code == 201:  # Created
            created_issue = response.json().get("issue")
            logger.info(f"Issue #{created_issue.get('id') if created_issue else 'Unknown ID'} created successfully: {subject[:50]}...")
            return created_issue
        else:
            logger.error(f"Failed to create issue: {response.status_code} - {response.text}")
            return None
