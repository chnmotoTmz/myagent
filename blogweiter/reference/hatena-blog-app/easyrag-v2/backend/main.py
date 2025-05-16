import sys
import os
import uvicorn
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from services.content_processor import ContentProcessor
from services.simple_search_service import SimpleSearchService
import json
from pathlib import Path
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from routers import files, rag, seed, article, image  # ルーターをインポート
from collections import defaultdict


# 環境変数の読み込み
load_dotenv()
NAS_API_URL = os.getenv('NAS_API_URL', 'http://chanmoto.synology.me:22358').rstrip('/')  # 末尾のスラッシュを削除
NAS_API_KEY = os.getenv('NAS_API_KEY', 'key')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # OpenAI APIキーを追加

# ロギングの設定
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = log_dir / f"api_{timestamp}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"ログファイル: {log_file}")

app = FastAPI()

# CORS設定を更新
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite開発サーバー
        "http://localhost:3000",  # 他の開発サーバー
        "http://localhost:8000",  # FastAPI自身
        "*"  # すべてのオリジンを許可（開発時のみ。本番環境では具体的なオリジンを指定することを推奨）
    ],
    allow_credentials=True,
    allow_methods=["*"],  # すべてのHTTPメソッドを許可
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "Accept",
        "*"  # すべてのヘッダーを許可
    ],
    expose_headers=["*"],  # レスポンスヘッダーの公開
    max_age=3600,  # プリフライトリクエストのキャッシュ時間（秒）
)

# サービスの初期化
content_processor = ContentProcessor(api_token=OPENAI_API_KEY)  # APIトークンを渡す
search_service = SimpleSearchService()

# メッセージファイルのディレクトリ（絶対パスで指定）
MESSAGE_DIR = Path(__file__).parent / "line_messages"
logger.info(f"メッセージディレクトリ: {MESSAGE_DIR}")

# NAS APIヘッダー
NAS_HEADERS = {
    'Accept': 'application/json',
    'X-API-Key': NAS_API_KEY
}

# メッセージバッファの設定
message_buffer = defaultdict(list)
buffer_tasks = {}
BUFFER_TIMEOUT = 60  # seconds

async def save_grouped_messages(user_id: str, messages: list) -> Path:
    """グループ化されたメッセージを保存する"""
    messages_dir = Path('line_messages')
    messages_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    filepath = messages_dir / f"{user_id}_{timestamp}.json"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    
    return filepath

async def save_image(message_id: str) -> str:
    """画像を保存して保存先パスを返す"""
    try:
        image_content = await download_line_image(message_id)
        if not image_content:
            return None
        
        image_dir = Path('line_images')
        image_dir.mkdir(exist_ok=True)
        image_path = image_dir / f"{message_id}.jpg"
        
        with open(image_path, 'wb') as f:
            f.write(image_content)
        
        return str(image_path)
    except Exception as e:
        logger.error(f"Error saving image: {e}")
        return None

async def process_buffered_messages(user_id: str):
    """バッファされたメッセージを処理"""
    if user_id not in message_buffer:
        return None
    
    messages = message_buffer[user_id]
    if not messages:
        return None
    
    filepath = await save_grouped_messages(user_id, messages)
    message_buffer[user_id] = []  # バッファをクリア
    
    return filepath

async def schedule_buffer_processing(user_id: str):
    """バッファ処理のスケジューリング"""
    if user_id in buffer_tasks:
        buffer_tasks[user_id].cancel()
    
    async def delayed_processing():
        await asyncio.sleep(BUFFER_TIMEOUT)
        await process_buffered_messages(user_id)
        buffer_tasks.pop(user_id, None)
    
    buffer_tasks[user_id] = asyncio.create_task(delayed_processing())

@app.post("/api/webhook/line")
async def webhook(request: Request):
    try:
        headers = dict(request.headers)
        logger.info(f"Received webhook request with headers: {json.dumps(headers, indent=2)}")

        data = await request.json()
        logger.info(f"Webhook request body: {json.dumps(data, indent=2)}")

        user_id = data.get('user')
        message_type = data.get('type')
        message_ids = data.get('messageIds', [data.get('messageId')])

        if user_id and message_type:
            timestamp_str = data.get('timestamp')
            try:
                if isinstance(timestamp_str, str):
                    timestamp_dt = datetime.fromisoformat(timestamp_str.rstrip('Z'))
                    timestamp_ms = int(timestamp_dt.timestamp() * 1000)
                else:
                    timestamp_ms = int(timestamp_str)
                
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc) + timedelta(hours=9)
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid timestamp format: {timestamp_str}")
                raise HTTPException(status_code=400, detail="Invalid timestamp format")

            message_data = {
                'type': message_type,
                'content': data.get('message', ''),
                'timestamp': timestamp.isoformat(),
                'message_id': data.get('messageId')
            }

            if message_type == 'image':
                image_path = await save_image(message_data['message_id'])
                if image_path:
                    message_data['file_path'] = image_path
                    logger.info(f"Image saved: {image_path}")

            message_buffer[user_id].append(message_data)
            logger.info(f"Message added to buffer for user {user_id}. Buffer size: {len(message_buffer[user_id])}")

            await schedule_buffer_processing(user_id)

            return {"status": "ok", "buffered": True}
        else:
            logger.warning("Invalid webhook data format")
            return {"status": "error", "message": "Invalid data format"}

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# シャットダウン時のイベントハンドラ
@app.on_event("shutdown")
async def shutdown_event():
    for user_id in list(message_buffer.keys()):
        await process_buffered_messages(user_id)

# ルーターを追加
app.include_router(files.router, tags=["Files"])
app.include_router(rag.router, prefix="/api", tags=["RAG"])
app.include_router(seed.router, prefix="/generate", tags=["Seed"])
app.include_router(article.router, prefix="/api", tags=["Article"])
app.include_router(image.router, tags=["Image"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
