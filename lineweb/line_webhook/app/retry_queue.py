import json
import os
from datetime import datetime
import logging
from typing import Dict, Optional
import asyncio
from pathlib import Path
import traceback

# Import STORAGE_PATH from config
from .config import STORAGE_PATH

logger = logging.getLogger(__name__)

class RetryQueue:
    def __init__(self):
        """初期化"""
        self.queue_dir = Path(STORAGE_PATH) / 'retry_queue'
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._setup_logging()

    def _setup_logging(self):
        """リトライキュー専用のログ設定"""
        log_dir = Path('logs/retry_queue')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # メインのログファイル
        main_log = log_dir / 'retry_queue.log'
        main_handler = logging.FileHandler(main_log)
        main_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
        )
        logger.addHandler(main_handler)
        
        # エラー詳細用のログファイル
        error_log = log_dir / 'retry_queue_errors.log'
        error_handler = logging.FileHandler(error_log)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d]\n%(message)s\n%(exc_info)s\n')
        )
        logger.addHandler(error_handler)

    def _log_failure(self, message_id: str, error: Exception, context: Dict = None):
        """エラー情報の詳細なログを記録"""
        error_info = {
            'message_id': message_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat(),
            'stack_trace': traceback.format_exc(),
            'context': context or {}
        }
        
        logger.error(
            f"Message {message_id} failed:\n" + 
            json.dumps(error_info, ensure_ascii=False, indent=2)
        )
        
        # エラー統計用のJSONファイルに保存
        stats_dir = self.queue_dir.parent / 'error_stats'
        stats_dir.mkdir(exist_ok=True)
        
        stats_file = stats_dir / f"error_{datetime.now().strftime('%Y%m')}.json"
        try:
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            else:
                stats = []
                
            stats.append(error_info)
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save error stats: {e}")

    async def add_to_queue(self, message_id: str, data: Dict) -> bool:
        """Add a failed request to the retry queue"""
        async with self._lock:
            try:
                queue_item = {
                    'message_id': message_id,
                    'data': data,
                    'attempts': 0,
                    'last_attempt': None,
                    'created_at': datetime.now().isoformat(),
                    'error_history': []  # エラー履歴を追加
                }
                
                file_path = self.queue_dir / f"{message_id}.json"
                
                # Ensure atomic write by using a temporary file
                temp_path = file_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(queue_item, f, ensure_ascii=False, indent=2)
                
                # Atomic rename
                temp_path.rename(file_path)
                
                logger.info(f"Added message {message_id} to retry queue")
                return True
                
            except Exception as e:
                self._log_failure(message_id, e, {'data': data})
                return False

    async def get_next_item(self) -> Optional[Dict]:
        """Get the next item to retry"""
        async with self._lock:
            try:
                # Find the oldest file that's ready for retry
                now = datetime.now()
                oldest_file = None
                oldest_time = None

                for file_path in self.queue_dir.glob('*.json'):
                    if file_path.suffix == '.tmp':
                        continue
                        
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            item = json.load(f)
                            
                        # Skip if too many attempts
                        if item['attempts'] >= 5:
                            logger.warning(f"Message {item['message_id']} exceeded retry limit")
                            continue
                            
                        # Check if enough time has passed since last attempt
                        if item['last_attempt']:
                            last_attempt = datetime.fromisoformat(item['last_attempt'])
                            delay = min(30, 2 ** item['attempts']) # Exponential backoff
                            if (now - last_attempt).total_seconds() < delay:
                                continue
                                
                        created_at = datetime.fromisoformat(item['created_at'])
                        if not oldest_time or created_at < oldest_time:
                            oldest_time = created_at
                            oldest_file = file_path
                            
                    except Exception as e:
                        logger.error(f"Error reading queue item {file_path}: {e}", exc_info=True)
                        continue

                if oldest_file:
                    with open(oldest_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                        
                return None
                
            except Exception as e:
                logger.error(f"Error getting next queue item: {e}", exc_info=True)
                return None

    async def update_item(self, message_id: str, success: bool, error: Exception = None) -> bool:
        """キューに入っているアイテムのステータスを更新"""
        async with self._lock:
            try:
                file_path = self.queue_dir / f"{message_id}.json"
                if not file_path.exists():
                    return False

                with open(file_path, 'r', encoding='utf-8') as f:
                    item = json.load(f)

                if success:
                    # 成功した場合はファイルを削除
                    file_path.unlink()
                    logger.info(f"Removed successful retry item {message_id}")
                else:
                    # エラー情報を記録
                    error_info = {
                        'attempt': item['attempts'] + 1,
                        'timestamp': datetime.now().isoformat(),
                        'error_type': type(error).__name__ if error else 'Unknown',
                        'error_message': str(error) if error else 'Unknown error'
                    }
                    item['error_history'].append(error_info)
                    
                    # 試行回数とタイムスタンプを更新
                    item['attempts'] += 1
                    item['last_attempt'] = datetime.now().isoformat()
                    
                    if item['attempts'] >= 5:
                        # リトライ上限に達した場合は失敗ディレクトリへ移動
                        failed_dir = self.queue_dir.parent / 'failed_retries'
                        failed_dir.mkdir(exist_ok=True)
                        file_path.replace(failed_dir / file_path.name)
                        logger.warning(
                            f"Moved {message_id} to failed retries after {item['attempts']} attempts\n" +
                            f"Error history:\n{json.dumps(item['error_history'], indent=2)}"
                        )
                    else:
                        # 更新されたデータを一時ファイルに書き込み
                        temp_path = file_path.with_suffix('.tmp')
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            json.dump(item, f, ensure_ascii=False, indent=2)
                        # replace()を使用して既存のファイルを上書き
                        temp_path.replace(file_path)
                        
                return True
                
            except Exception as e:
                self._log_failure(message_id, e, {'success': success})
                return False

    async def cleanup(self, max_age_hours: int = 24):
        """Clean up old queue items"""
        async with self._lock:
            try:
                now = datetime.now()
                for file_path in self.queue_dir.glob('*.json'):
                    try:
                        if file_path.suffix == '.tmp':
                            # Delete old temp files
                            if (now - datetime.fromtimestamp(file_path.stat().st_mtime)).total_seconds() > 3600:
                                file_path.unlink()
                                logger.info(f"Deleted old temp file: {file_path}")
                            continue

                        with open(file_path, 'r', encoding='utf-8') as f:
                            item = json.load(f)
                            
                        created_at = datetime.fromisoformat(item['created_at'])
                        if (now - created_at).total_seconds() > max_age_hours * 3600:
                            # Move to failed queue
                            failed_dir = self.queue_dir.parent / 'failed_retries'
                            failed_dir.mkdir(exist_ok=True)
                            file_path.rename(failed_dir / file_path.name)
                            logger.info(
                                f"Moved old item {item['message_id']} to failed retries\n" +
                                f"Age: {(now - created_at).total_seconds() / 3600:.1f} hours"
                            )
                            
                    except Exception as e:
                        logger.error(f"Error cleaning up queue item {file_path}: {e}", exc_info=True)
                        
            except Exception as e:
                logger.error(f"Error during queue cleanup: {e}", exc_info=True)

    async def remove_item(self, message_id: str) -> bool:
        """キューからアイテムを削除"""
        async with self._lock:
            try:
                file_path = self.queue_dir / f"{message_id}.json"
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Removed item {message_id} from retry queue")
                    return True
                else:
                    logger.warning(f"Item {message_id} not found in retry queue")
                    return False
            except Exception as e:
                logger.error(f"Error removing item {message_id} from retry queue: {e}")
                return False

# Global retry queue instance
retry_queue = RetryQueue()