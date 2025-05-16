import logging
import httpx
import os
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def call_content_service(data: Dict[str, Any]) -> bool:
    """コンテンツサービスにデータを送信"""
    content_service_url = os.getenv('CONTENT_SERVICE_URL', 'http://localhost:8001/api/receive_message')
    logger.info(f"コンテンツサービスにデータを送信: {content_service_url}")
    
    timeout = httpx.Timeout(5.0, connect=2.0)  # タイムアウトを短く設定

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                content_service_url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            logger.info(f"コンテンツサービスへの送信成功: {response.status_code}")
            return True
                
    except httpx.ConnectError as e:
        logger.warning(f"コンテンツサービスに接続できません: {e}")
        return False
            
    except httpx.TimeoutException as e:
        logger.warning(f"コンテンツサービスの応答がありません: {e}")
        return False
            
    except Exception as e:
        logger.error(f"コンテンツサービスの送信中にエラーが発生: {e}", exc_info=True)
        return False

async def notify_bundle_completion(user_id: str, success: bool):
    """ユーザーにメッセージ処理の完了ステータスを通知"""
    if success:
        message = "メッセージの処理が完了しました。"
        logger.info(f"Notifying user {user_id} of successful processing.")
    else:
        message = "メッセージの処理中にエラーが発生しました。詳細はログを確認してください。"
        logger.warning(f"Notifying user {user_id} of processing failure.")
    
    # LINE APIを使用して通知
    from .main import send_line_message
    return await send_line_message(user_id, message)