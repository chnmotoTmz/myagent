"""
Redmineチケット管理エージェント

毎日の予定と実績を管理し、LINEを通じてユーザーとやり取りするエージェント。
"""
import os
import requests
import datetime
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/redmine_agent.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("redmine_agent")

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
        
        params = {
            "start_date": today,
            "due_date": today,
            "status_id": "open",
            "sort": "priority:desc",
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
            logger.error(f"Failed to get daily tasks: {response.text}")
            return []
            
        data = response.json()
        return data.get("issues", [])
    
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
    
    def get_time_entries(self, user_id: Optional[int] = None, from_date: Optional[str] = None,
                         to_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        作業時間エントリの取得
        
        Args:
            user_id: ユーザーID (省略時は全ユーザー)
            from_date: 開始日 (YYYY-MM-DD形式)
            to_date: 終了日 (YYYY-MM-DD形式)
            
        Returns:
            作業時間エントリ一覧
        """
        params = {"limit": 100}
        
        if user_id:
            params["user_id"] = user_id
            
        if from_date:
            params["from"] = from_date
            
        if to_date:
            params["to"] = to_date
            
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
    
    def format_morning_report(self, tasks: List[Dict[str, Any]]) -> str:
        """
        朝の予定レポートを整形
        
        Args:
            tasks: タスク一覧
            
        Returns:
            整形されたレポート文字列
        """
        today = datetime.date.today().strftime("%Y年%m月%d日")
        report = f"【{today} 本日の予定】\n\n"
        
        if not tasks:
            return report + "予定されているタスクはありません。"
        
        for i, task in enumerate(tasks, 1):
            priority = task.get("priority", {}).get("name", "中")
            subject = task.get("subject", "無題")
            estimate = task.get("estimated_hours", "未設定")
            
            report += f"{i}. {subject} (優先度:{priority}, 見積:{estimate}h)\n"
            
        report += "\n今日も良い一日を！"
        return report
    
    def format_evening_report(self, completed_tasks: List[Dict[str, Any]], 
                             time_entries: List[Dict[str, Any]]) -> str:
        """
        夜の実績レポートを整形
        
        Args:
            completed_tasks: 完了したタスク一覧
            time_entries: 作業時間エントリ一覧
            
        Returns:
            整形されたレポート文字列
        """
        today = datetime.date.today().strftime("%Y年%m月%d日")
        report = f"【{today} 本日の実績】\n\n"
        
        # 総作業時間
        total_hours = sum(entry.get("hours", 0) for entry in time_entries)
        report += f"総作業時間: {total_hours}時間\n\n"
        
        # 完了タスク
        report += "■ 完了したタスク\n"
        if completed_tasks:
            for i, task in enumerate(completed_tasks, 1):
                subject = task.get("subject", "無題")
                report += f"{i}. {subject}\n"
        else:
            report += "完了したタスクはありません。\n"
            
        # 作業時間詳細
        report += "\n■ 作業時間詳細\n"
        if time_entries:
            for entry in time_entries:
                issue_id = entry.get("issue", {}).get("id", "不明")
                hours = entry.get("hours", 0)
                comments = entry.get("comments", "")
                report += f"- チケット#{issue_id}: {hours}時間 ({comments})\n"
        else:
            report += "記録された作業時間はありません。\n"
            
        report += "\nお疲れ様でした！"
        return report
    
    def generate_weekly_summary(self, from_date: Optional[str] = None) -> str:
        """
        週間サマリーレポートを生成
        
        Args:
            from_date: 開始日 (YYYY-MM-DD形式、省略時は1週間前)
            
        Returns:
            週間サマリーレポート
        """
        today = datetime.date.today()
        
        if not from_date:
            # 1週間前の日付
            from_date = (today - datetime.timedelta(days=7)).isoformat()
            
        # 期間中の作業時間エントリを取得
        time_entries = self.get_time_entries(from_date=from_date, to_date=today.isoformat())
        
        # チケットIDごとに作業時間を集計
        issue_hours = {}
        total_hours = 0
        
        for entry in time_entries:
            issue_id = entry.get("issue", {}).get("id")
            if issue_id:
                if issue_id not in issue_hours:
                    issue_hours[issue_id] = {
                        "hours": 0,
                        "issue_id": issue_id,
                        "comments": []
                    }
                
                hours = entry.get("hours", 0)
                issue_hours[issue_id]["hours"] += hours
                total_hours += hours
                
                comment = entry.get("comments")
                if comment:
                    issue_hours[issue_id]["comments"].append(comment)
        
        # チケット情報を取得
        for issue_id in issue_hours:
            response = requests.get(
                f"{self.redmine_url}/issues/{issue_id}.json",
                headers=self.headers
            )
            
            if response.status_code == 200:
                issue = response.json().get("issue", {})
                issue_hours[issue_id]["subject"] = issue.get("subject", "無題")
                issue_hours[issue_id]["status"] = issue.get("status", {}).get("name", "不明")
                issue_hours[issue_id]["done_ratio"] = issue.get("done_ratio", 0)
        
        # レポート作成
        from_date_formatted = datetime.datetime.fromisoformat(from_date).strftime("%Y年%m月%d日")
        today_formatted = today.strftime("%Y年%m月%d日")
        
        report = f"【週間サマリー: {from_date_formatted} ～ {today_formatted}】\n\n"
        report += f"総作業時間: {total_hours}時間\n\n"
        report += "■ チケット別作業時間\n"
        
        # 作業時間が多い順にソート
        sorted_issues = sorted(issue_hours.values(), key=lambda x: x["hours"], reverse=True)
        
        for issue in sorted_issues:
            subject = issue.get("subject", "無題")
            hours = issue["hours"]
            status = issue.get("status", "不明")
            done_ratio = issue.get("done_ratio", 0)
            
            report += f"- {subject} (#{issue['issue_id']})\n"
            report += f"  {hours}時間, 状態:{status}, 進捗:{done_ratio}%\n"
        
        return report
