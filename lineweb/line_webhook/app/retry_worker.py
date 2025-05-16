import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict

# Import STORAGE_PATH from config instead of main
from .config import STORAGE_PATH  # main.pyからconfigに変更
from .retry_queue import retry_queue
from .utils import notify_bundle_completion
import os  # Import os for path joining

logger = logging.getLogger(__name__)

# Global flag to control the worker
_worker_running = False
MAX_RETRIES = 3
RETRY_DELAY = 300  # 5分

async def start_retry_worker():
    global _worker_running
    
    if _worker_running:
        logger.warning("リトライワーカーは既に実行中です")
        return
        
    _worker_running = True
    logger.info("リトライワーカーを開始します")
    
    try:
        while _worker_running:
            try:
                await retry_queue.cleanup()
                item = await retry_queue.get_next_item()
                
                if not item:
                    await asyncio.sleep(5)
                    continue
                    
                message_id = item['message_id']
                data = item['data']
                retry_count = item.get('retry_count', 0)
                
                if retry_count >= MAX_RETRIES:
                    logger.error(f"メッセージ {message_id} の最大リトライ回数を超過")
                    await _handle_max_retries(item)
                    continue
                
                logger.info(f"メッセージ {message_id} の処理を再試行（{retry_count + 1}/{MAX_RETRIES}回目）")
                
                success = await _process_retry_item(data)
                
                if success:
                    logger.info(f"メッセージ {message_id} の再処理に成功")
                    await notify_bundle_completion(data.get('user_id'), True)
                    await retry_queue.remove_item(message_id)
                else:
                    logger.warning(f"メッセージ {message_id} の再処理に失敗")
                    await _handle_retry_failure(item)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"リトライワーカーのループでエラー発生: {e}", exc_info=True)
                await asyncio.sleep(5)
                
    except asyncio.CancelledError:
        logger.info("リトライワーカーのキャンセル要求を受信")
    finally:
        _worker_running = False
        logger.info("リトライワーカーを停止しました")

async def _handle_retry_failure(item: Dict):
    """リトライ失敗時の処理"""
    message_id = item['message_id']
    
    # 直接ファイルを更新せず、update_itemに準拠したパラメータのみ渡す
    await retry_queue.update_item(
        message_id,
        success=False
    )

async def _handle_max_retries(item: Dict):
    """最大リトライ回数超過時の処理"""
    message_id = item['message_id']
    data = item['data']
    
    # エラー詳細を保存
    failed_dir = os.path.join(STORAGE_PATH, 'failed_retries')
    error_path = os.path.join(failed_dir, f"{message_id}.json")
    try:
        with open(error_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"エラー情報の保存に失敗: {e}", exc_info=True)
    
    # ユーザーに通知
    if data.get('user_id'):
        await notify_bundle_completion(data['user_id'], False)
    
    # キューからアイテムを削除
    await retry_queue.remove_item(message_id)

async def stop_retry_worker():
    """リトライワーカーを停止"""
    global _worker_running
    _worker_running = False
    logger.info("リトライワーカーの停止を要求中...")

async def _process_retry_item(data: dict) -> bool:
    """リトライアイテムの処理"""
    try:
        from .main import call_content_service
        return await call_content_service(data)
    except Exception as e:
        logger.error(f"リトライアイテムの処理でエラー発生: {e}", exc_info=True)
        return False