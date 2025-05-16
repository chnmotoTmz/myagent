import os
import json
import logging
import asyncio
import uvicorn
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from linebot import LineBotApi
from contextlib import asynccontextmanager
from pydantic import BaseModel

# Use relative imports for app modules
from .organize_files import organize_files_by_type
from .message_bundler import process_new_message
from .retry_queue import retry_queue
from .retry_worker import start_retry_worker
from .utils import call_content_service
from .config import STORAGE_PATH

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('line_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# .envファイルの読み込み
try:
    env_path = Path(__file__).resolve().parent / '.env'
    load_dotenv(env_path)
    logger.info(f"Loaded environment variables from: {env_path}")
except Exception as e:
    logger.error(f"Could not load .env file: {e}")

# LINE API credentials
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_TOKEN')

if not LINE_CHANNEL_ACCESS_TOKEN:
    logger.error("LINE API token not found in environment variables.")
    line_bot_api = None
else:
    try:
        line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        logger.info("LINE Bot API initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize LINE Bot API: {e}")
        line_bot_api = None

# ストレージパスの設定
try:
    os.makedirs(STORAGE_PATH, exist_ok=True)
    logger.info(f"Storage path set to: {os.path.abspath(STORAGE_PATH)}")
except OSError as e:
    logger.error(f"Failed to create storage directory '{STORAGE_PATH}': {e}")

# 重複リクエストチェック用の辞書とロック
processed_requests = {}
processed_requests_lock = asyncio.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクルを管理"""
    # Startup
    task = asyncio.create_task(start_retry_worker())
    logger.info("Started retry queue worker background task.")
    yield
    # Shutdown処理が必要な場合はここに追加

app = FastAPI(
    title="LINE Webhook Service",
    description="Receives LINE Webhooks from GAS and handles content generation",
    version="1.0.1",
    lifespan=lifespan
)

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

def is_duplicate_request(request_id: str, timeout_minutes: int = 5) -> bool:
    """重複リクエストのチェック"""
    current_time = datetime.now()
    
    # 古いエントリの削除
    for rid, timestamp in list(processed_requests.items()):
        if (current_time - timestamp).total_seconds() > timeout_minutes * 60:
            processed_requests.pop(rid, None)
    
    if request_id in processed_requests:
        return True
    
    processed_requests[request_id] = current_time
    return False

async def send_line_message(user_id: str, message: str) -> bool:
    """LINEにメッセージを送信"""
    if not line_bot_api:
        logger.error("Cannot send LINE message: Access token not configured.")
        return False

    try:
        from linebot.models import TextMessage
        text_message = TextMessage(text=message)
        
        await asyncio.get_running_loop().run_in_executor(
            None,
            line_bot_api.push_message,
            user_id,
            text_message
        )
        logger.info(f"Successfully sent LINE message to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending LINE message: {e}", exc_info=True)
        return False

async def download_line_content(message_id: str) -> Optional[bytes]:
    """LINEからコンテンツをダウンロード"""
    if not line_bot_api:
        logger.error("Cannot download content: LINE API not initialized")
        return None

    try:
        message_content = await asyncio.get_running_loop().run_in_executor(
            None,
            line_bot_api.get_message_content,
            message_id
        )
        return message_content.content
    except Exception as e:
        logger.error(f"Error downloading content from LINE: {e}", exc_info=True)
        return None

async def process_message_bundle_async(user_id: str, file_path: str):
    """メッセージのバンドル処理を非同期で実行"""
    try:
        await asyncio.sleep(0.5)
        logger.info(f"Starting message bundle processing: user={user_id}, file={file_path}")
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process_new_message, user_id, file_path)
        
        logger.info(f"Message bundle processing completed: user={user_id}")
    except Exception as e:
        logger.error(f"Error in bundle processing: {e}", exc_info=True)
        await send_line_message(
            user_id,
            "メッセージの処理中にエラーが発生しました。"
        )

@app.post("/api/webhook/line")
async def webhook(request: Request):
    """GASからのWebhookを処理"""
    data = await request.json()
    logger.info(f"Received webhook data: {data}")
    
    # 必要なフィールドの検証
    required_fields = ['user', 'type', 'message']
    for field in required_fields:
        if field not in data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )

    user_id = data['user']
    message_type = data['type']
    message_id = data.get('messageId', datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    
    # 重複チェック
    request_id = f"{user_id}_{message_id}"
    async with processed_requests_lock:
        if is_duplicate_request(request_id):
            logger.info(f"Duplicate message skipped: {request_id}")
            return {"status": "ok", "detail": "Duplicate message"}

    # ユーザーディレクトリの準備
    user_dir = os.path.join(STORAGE_PATH, user_id)
    os.makedirs(user_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    filepath = None
    content = None

    try:
        # メッセージタイプに応じた処理
        if message_type == 'text':
            content = str(data['message'])
            filepath = os.path.join(user_dir, f"{timestamp}.txt")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Text saved to: {filepath}")
        
        elif message_type in ['image', 'video']:
            extension = '.jpg' if message_type == 'image' else '.mp4'
            filepath = os.path.join(user_dir, f"{timestamp}{extension}")
            # ファイルの保存は非同期で行う
            asyncio.create_task(save_media_file(data.get('message'), filepath))
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported message type: {message_type}"
            )

        # 即座にWebhookのレスポンスを返す
        response_data = {
            "status": "ok",
            "message": "Message received",
            "filepath": filepath,
            "content": content if message_type == 'text' else None
        }

        # バックグラウンドでコンテンツサービスとLINE APIの処理を行う
        service_data = {
            "user_id": user_id,
            "message_id": message_id,
            "message_type": message_type,
            "filepath": filepath,
            "content": content
        }
        # コンテンツサービスへの非同期通知を有効化
        asyncio.create_task(process_message_async(service_data, user_id))
        
        return response_data

    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def save_media_file(message_id: str, filepath: str):
    """メディアファイルを非同期で保存"""
    try:
        file_content = await download_line_content(message_id)
        if file_content:
            with open(filepath, "wb") as f:
                f.write(file_content)
            logger.info(f"Media file saved to: {filepath}")
        else:
            logger.error(f"Failed to download media content for message {message_id}")
    except Exception as e:
        logger.error(f"Error saving media file: {e}", exc_info=True)

async def process_message_async(service_data: Dict[str, Any], user_id: str):
    """メッセージの非同期処理"""
    try:
        # コンテンツサービスの呼び出し
        success = await call_content_service(service_data)
        
        if not success:
            logger.warning(f"Content service call failed for {service_data['message_id']}")
            await retry_queue.add_to_queue(service_data['message_id'], service_data)
            # LINE通知は非同期で送信
            asyncio.create_task(send_line_message(
                user_id,
                "メッセージを受け付けました。処理に時間がかかる場合があります。"
            ))
        
        # バンドル処理を非同期で開始
        asyncio.create_task(process_message_bundle_async(user_id, service_data['filepath']))
        
    except Exception as e:
        logger.error(f"Error in async message processing: {e}", exc_info=True)

class MessageReceiveRequest(BaseModel):
    user_id: str
    message_id: str
    message_type: str
    filepath: str | None
    content: str | None

@app.post("/api/receive_message")
async def receive_message(request: MessageReceiveRequest):
    """記事生成サービスからのメッセージを処理"""
    logger.info(f"Received message from article service: {request}")
    
    try:
        service_data = {
            "user_id": request.user_id,
            "message_id": request.message_id,
            "message_type": request.message_type,
            "filepath": request.filepath,
            "content": request.content
        }
        
        # バンドル処理を非同期で実行
        if request.filepath:
            asyncio.create_task(process_message_bundle_async(request.user_id, request.filepath))
        
        # ユーザーに通知
        asyncio.create_task(send_line_message(
            request.user_id,
            "メッセージを受信しました。処理を開始します。"
        ))
        
        return {"status": "ok", "message": "Message received and processing started"}
        
    except Exception as e:
        logger.error(f"Error processing received message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8083'))
    uvicorn.run(app, host=host, port=port, reload=True)
