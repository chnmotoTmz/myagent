import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
from typing import Dict, List, Optional

from .retry_queue import retry_queue

logger = logging.getLogger(__name__)

class RetryQueueMonitor:
    def __init__(self):
        self.stats_dir = Path('storage/error_stats')
        self.stats_dir.mkdir(parents=True, exist_ok=True)

    async def get_queue_status(self) -> Dict:
        """リトライキューの現在の状態を取得"""
        queue_items = []
        total_items = 0
        retry_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

        for file_path in retry_queue.queue_dir.glob('*.json'):
            if file_path.suffix == '.tmp':
                continue

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    item = json.load(f)
                    total_items += 1
                    attempts = item.get('attempts', 0)
                    retry_counts[attempts] = retry_counts.get(attempts, 0) + 1
                    queue_items.append({
                        'message_id': item['message_id'],
                        'attempts': attempts,
                        'last_attempt': item.get('last_attempt'),
                        'created_at': item['created_at']
                    })
            except Exception as e:
                logger.error(f"Error reading queue item {file_path}: {e}")

        return {
            'total_items': total_items,
            'retry_counts': retry_counts,
            'items': queue_items
        }

    async def get_error_stats(self, days: int = 7) -> Dict:
        """エラー統計情報を取得"""
        stats = []
        start_date = datetime.now() - timedelta(days=days)

        for stats_file in self.stats_dir.glob('error_*.json'):
            try:
                with open(stats_file, 'r', encoding='utf-8') as f:
                    file_stats = json.load(f)
                    for error in file_stats:
                        error_time = datetime.fromisoformat(error['timestamp'])
                        if error_time >= start_date:
                            stats.append(error)
            except Exception as e:
                logger.error(f"Error reading stats file {stats_file}: {e}")

        error_types = {}
        daily_counts = {}
        for error in stats:
            error_type = error['error_type']
            error_time = datetime.fromisoformat(error['timestamp'])
            date_str = error_time.date().isoformat()

            error_types[error_type] = error_types.get(error_type, 0) + 1
            if date_str not in daily_counts:
                daily_counts[date_str] = {
                    'total': 0,
                    'by_type': {}
                }
            daily_counts[date_str]['total'] += 1
            daily_counts[date_str]['by_type'][error_type] = \
                daily_counts[date_str]['by_type'].get(error_type, 0) + 1

        return {
            'total_errors': len(stats),
            'error_types': error_types,
            'daily_counts': daily_counts
        }

    async def get_failed_retries(self) -> List[Dict]:
        """失敗したリトライの一覧を取得"""
        failed_dir = retry_queue.queue_dir.parent / 'failed_retries'
        if not failed_dir.exists():
            return []

        failed_items = []
        for file_path in failed_dir.glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    item = json.load(f)
                    failed_items.append({
                        'message_id': item['message_id'],
                        'created_at': item['created_at'],
                        'error_history': item.get('error_history', [])
                    })
            except Exception as e:
                logger.error(f"Error reading failed retry {file_path}: {e}")

        return failed_items

# グローバルモニターインスタンス
retry_monitor = RetryQueueMonitor()