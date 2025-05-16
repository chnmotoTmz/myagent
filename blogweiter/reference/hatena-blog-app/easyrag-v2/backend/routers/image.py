from fastapi import APIRouter, HTTPException
import logging
import requests
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()
NAS_API_URL = os.getenv('NAS_API_URL', 'http://chanmoto.synology.me:22358')
NAS_API_KEY = os.getenv('NAS_API_KEY', 'key')

# NAS APIヘッダー
NAS_HEADERS = {
    'Accept': '*/*',
    'X-API-Key': NAS_API_KEY
}

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/image/{image_id}")
async def get_image(image_id: str):
    """指定されたIDの画像を取得"""
    try:
        response = requests.get(
            f"{NAS_API_URL}/image/{image_id}",
            headers=NAS_HEADERS
        )
        
        if not response.ok:
            raise HTTPException(
                status_code=response.status_code,
                detail="画像の取得に失敗しました"
            )
        
        return response.content  # 画像データを返す
        
    except Exception as e:
        logger.error(f"画像取得エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 