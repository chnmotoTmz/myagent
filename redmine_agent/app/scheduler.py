"""
Redmineチケット管理エージェント - スケジューラ

定期的なタスクの実行を管理するスケジューラコンポーネント。
"""

import asyncio
import datetime
import logging
import pytz
from typing import Dict, Any, List
import json

from .core import RedmineAgent
from .linebot_adapter import LineBotAdapter
from .config import get_config

# 共通ロガー設定
logger = logging.getLogger(__name__)

async def schedule_daily_tasks(line_adapter: LineBotAdapter, redmine_agent: RedmineAgent, 
                               user_id_mapping: Dict[str, str]):
    """
    毎日のタスクをスケジュール
    
    Args:
        line_adapter: LINE Botアダプター
        redmine_agent: Redmineエージェント
        user_id_mapping: RedmineユーザーIDとLINE ユーザーIDのマッピング
    """
    while True:
        now = datetime.datetime.now()
        
        # 設定から時間を取得
        morning_time = get_config("notification.morning_report_time") or "09:00"
        evening_time = get_config("notification.evening_report_time") or "18:30"
        morning_enabled = get_config("notification.morning_report_enabled")
        evening_enabled = get_config("notification.evening_report_enabled")
        
        # 文字列の時間を時間と分に分解
        morning_hour, morning_minute = map(int, morning_time.split(":"))
        evening_hour, evening_minute = map(int, evening_time.split(":"))
        
        # 朝レポート
        morning_target = now.replace(hour=morning_hour, minute=morning_minute, second=0, microsecond=0)
        if morning_enabled is not False and now < morning_target:
            # 朝のレポート時間前の場合
            wait_seconds = (morning_target - now).total_seconds()
            logger.info(f"朝レポートまで {wait_seconds:.2f} 秒待機します")
            await asyncio.sleep(wait_seconds)
            await send_morning_reports(line_adapter, redmine_agent, user_id_mapping)
        
        # 夜レポート
        evening_target = now.replace(hour=evening_hour, minute=evening_minute, second=0, microsecond=0)
        if evening_enabled is not False and now < evening_target:
            # 夜のレポート時間前の場合
            wait_seconds = (evening_target - now).total_seconds()
            logger.info(f"夕方レポートまで {wait_seconds:.2f} 秒待機します")
            await asyncio.sleep(wait_seconds)
            await send_evening_reports(line_adapter, redmine_agent, user_id_mapping)
        
        # 次の日の朝まで待機
        tomorrow = now + datetime.timedelta(days=1)
        next_morning = tomorrow.replace(hour=morning_hour, minute=morning_minute, second=0, microsecond=0)
        wait_seconds = (next_morning - now).total_seconds()
        logger.info(f"Waiting {wait_seconds:.2f} seconds until next day's schedule")
        await asyncio.sleep(wait_seconds)

async def send_morning_reports(line_adapter: LineBotAdapter, redmine_agent: RedmineAgent,
                               user_id_mapping: Dict[str, str]):
    """
    朝のレポートを送信
    
    Args:
        line_adapter: LINE Botアダプター
        redmine_agent: Redmineエージェント
        user_id_mapping: RedmineユーザーIDとLINE ユーザーIDのマッピング
    """
    logger.info("Sending morning reports")
    
    for redmine_user_id, line_user_id in user_id_mapping.items():
        try:
            tasks = redmine_agent.get_daily_tasks(user_id=int(redmine_user_id))
            report = redmine_agent.format_morning_report(tasks)
            
            success = line_adapter.send_message(line_user_id, report)
            
            if success:
                logger.info(f"Morning report sent to LINE user {line_user_id}")
            else:
                logger.error(f"Failed to send morning report to LINE user {line_user_id}")
        except Exception as e:
            logger.error(f"Error sending morning report: {e}", exc_info=True)

async def send_evening_reports(line_adapter: LineBotAdapter, redmine_agent: RedmineAgent,
                               user_id_mapping: Dict[str, str]):
    """
    夜のレポートを送信
    
    Args:
        line_adapter: LINE Botアダプター
        redmine_agent: Redmineエージェント
        user_id_mapping: RedmineユーザーIDとLINE ユーザーIDのマッピング
    """
    logger.info("Sending evening reports")
    today = datetime.date.today().isoformat()
    
    for redmine_user_id, line_user_id in user_id_mapping.items():
        try:
            # 今日の作業時間を取得
            time_entries = redmine_agent.get_time_entries(
                user_id=int(redmine_user_id),
                from_date=today,
                to_date=today
            )
            
            # 完了したタスク（ステータスが変わったチケットを取得する拡張が必要）
            completed_tasks = []
            
            report = redmine_agent.format_evening_report(completed_tasks, time_entries)
            
            success = line_adapter.send_message(line_user_id, report)
            
            if success:
                logger.info(f"Evening report sent to LINE user {line_user_id}")
            else:
                logger.error(f"Failed to send evening report to LINE user {line_user_id}")
                
            # 効率化提案も送信（週1回、金曜日）
            if datetime.date.today().weekday() == 4:  # 金曜日
                optimization = redmine_agent.suggest_task_consolidation()
                if optimization:
                    line_adapter.send_message(line_user_id, optimization)
        except Exception as e:
            logger.error(f"Error sending evening report: {e}", exc_info=True)

async def start_scheduler(line_adapter: LineBotAdapter, redmine_agent: RedmineAgent,
                          user_id_mapping: Dict[str, str]):
    """
    スケジューラを開始
    
    Args:
        line_adapter: LINE Botアダプター
        redmine_agent: Redmineエージェント
        user_id_mapping: RedmineユーザーIDとLINE ユーザーIDのマッピング
    """
    logger.info("Starting scheduler")
    await schedule_daily_tasks(line_adapter, redmine_agent, user_id_mapping)
