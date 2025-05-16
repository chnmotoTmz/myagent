"""
NLPヘルパー

自然言語メッセージからコマンドの意図とパラメータを抽出するためのユーティリティ関数。
これはLLMが利用できない場合のフォールバックメカニズムとして機能します。
"""

import re
import logging
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)

def extract_command_intent(text: str) -> Tuple[str, str]:
    """
    メッセージテキストからコマンドの意図とパラメータを抽出
    
    Args:
        text: メッセージテキスト
        
    Returns:
        (コマンド, パラメータ)のタプル
    """
    text = text.lower()
    
    # 今日のタスクを確認
    if any(keyword in text for keyword in ["今日のタスク", "今日の予定", "本日のタスク", "本日の予定"]):
        return "today", ""
    
    # 今後のタスクを確認
    if any(keyword in text for keyword in ["今後のタスク", "予定", "スケジュール", "今後"]):
        # 日数を抽出
        days_match = re.search(r'(\d+)\s*(日|days)', text)
        if days_match:
            days = days_match.group(1)
            return "tasks", days + "日"
        return "tasks", ""
    
    # 作業時間記録
    if any(keyword in text for keyword in ["記録", "時間", "ログ", "作業"]):
        # チケット番号を抽出
        ticket_match = re.search(r'[#]?(\d+)', text)
        if not ticket_match:
            return "help", "チケット番号が見つかりません"
            
        issue_id = ticket_match.group(1)
        
        # 時間数を抽出
        hours_match = re.search(r'(\d+\.?\d*)\s*(時間|hours?|h)', text)
        if not hours_match:
            return "help", "作業時間が見つかりません"
            
        hours = hours_match.group(1)
        
        # コメント部分を抽出
        for pattern in [
            r'内容[はが：:]\s*「?([^」]+)」?',
            r'コメント[はが：:]\s*「?([^」]+)」?',
            r'「([^」]+)」',
        ]:
            comment_match = re.search(pattern, text)
            if comment_match:
                comment = comment_match.group(1)
                return "log", f"{issue_id} {hours} {comment}"
        
        # コメント部分が見つからない場合
        return "log", f"{issue_id} {hours}"
    
    # ステータス更新
    if any(keyword in text for keyword in ["ステータス", "状態"]):
        # チケット番号を抽出
        ticket_match = re.search(r'[#]?(\d+)', text)
        if not ticket_match:
            return "help", "チケット番号が見つかりません"
            
        issue_id = ticket_match.group(1)
        
        # ステータスIDを抽出 (簡易的に数字を検索)
        status_match = re.search(r'ステータス\s*[を]?\s*(\d+)', text)
        if status_match:
            status_id = status_match.group(1)
            return "status", f"{issue_id} {status_id}"
        
        # ステータス名から推測
        if "完了" in text or "done" in text:
            return "status", f"{issue_id} 5"  # 5 = 完了 (要確認)
        elif "進行中" in text or "in progress" in text:
            return "status", f"{issue_id} 2"  # 2 = 進行中 (要確認)
        
        return "help", "ステータスが特定できません"
    
    # 進捗更新
    if any(keyword in text for keyword in ["進捗", "完了率", "進度"]):
        # チケット番号を抽出
        ticket_match = re.search(r'[#]?(\d+)', text)
        if not ticket_match:
            return "help", "チケット番号が見つかりません"
            
        issue_id = ticket_match.group(1)
        
        # 進捗率を抽出
        progress_match = re.search(r'(\d+)\s*[%％]', text)
        if progress_match:
            progress = progress_match.group(1)
            
            # コメント部分を抽出
            comment_match = re.search(r'内容[はが：:]\s*「?([^」]+)」?', text)
            comment = comment_match.group(1) if comment_match else ""
            
            return "update", f"{issue_id} {progress} {comment}".strip()
        
        return "help", "進捗率が特定できません"
    
    # チケット要約
    if any(keyword in text for keyword in ["要約", "サマリー", "詳細"]):
        # チケット番号を抽出
        ticket_match = re.search(r'[#]?(\d+)', text)
        if ticket_match:
            issue_id = ticket_match.group(1)
            return "summary", issue_id
        
        return "help", "チケット番号が見つかりません"
    
    # レポート
    if any(keyword in text for keyword in ["レポート", "報告"]):
        if any(keyword in text for keyword in ["週間", "ウィーク", "週次"]):
            return "report", "week"
        else:
            return "report", "today"
    
    # 効率化提案
    if any(keyword in text for keyword in ["効率", "最適", "統合", "まとめ"]):
        return "optimize", ""
    
    # コマンドが特定できない場合
    return "help", ""
