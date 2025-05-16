from fastapi import APIRouter, HTTPException
import logging
import requests
import os
from dotenv import load_dotenv
import json

# 環境変数の読み込み
load_dotenv()
NAS_API_URL = os.getenv('NAS_API_URL', 'http://chanmoto.synology.me:22358')
NAS_API_KEY = os.getenv('NAS_API_KEY', 'key')

# NAS APIヘッダー
NAS_HEADERS = {
    'Accept': '*/*',  # ファイル取得用のヘッダー
    'X-API-Key': NAS_API_KEY
}

# ファイル一覧取得用のヘッダー
LIST_HEADERS = {
    'Accept': 'application/json',  # 一覧取得用のヘッダー
    'X-API-Key': NAS_API_KEY
}

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/files")
async def get_files():
    """LINEメッセージの一覧を取得"""
    try:
        logger.info("NAS APIからファイル一覧を取得中...")
        
        url = f"{NAS_API_URL}/files"
        logger.info(f"URL: {url}")
        
        # 一覧取得用のヘッダーを使用
        response = requests.get(
            url,
            headers=LIST_HEADERS,  # 一覧取得用のヘッダーを使用
            timeout=10
        )
        
        if not response.ok:
            logger.error(f"NAS APIエラー: {response.status_code}")
            logger.error(f"レスポンス: {response.text}")
            if response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="APIへのアクセス権限がありません。APIキーを確認してください。"
                )
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ファイル一覧の取得に失敗しました: {response.text}"
            )

        files = response.json()
        logger.info(f"取得したファイル数: {len(files) if isinstance(files, list) else 'N/A'}")

        return files

    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"予期せぬエラーが発生しました: {str(e)}"
        )

@router.get("/file/{file_path:path}")
async def get_file(file_path: str):
    """指定されたファイルの内容を取得"""
    try:
        logger.info(f"ファイル取得リクエスト: {file_path}")
        
        # ファイルパスの正規化
        normalized_path = file_path.replace('file/', '')
        if normalized_path.startswith('/'):
            normalized_path = normalized_path[1:]
            
        url = f"{NAS_API_URL}/file/{normalized_path}"
        logger.info(f"リクエストURL: {url}")
        
        # ファイル取得用のヘッダーを使用
        response = requests.get(
            url,
            headers=NAS_HEADERS,  # ファイル取得用のヘッダーを使用
            timeout=10
        )
        
        logger.info(f"NAS APIレスポンス: Status={response.status_code}")
        
        if not response.ok:
            logger.error(f"NAS APIエラー: {response.status_code} - {response.text}")
            if response.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="APIへのアクセス権限がありません。APIキーを確認してください。"
                )
            elif response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="指定されたファイルが見つかりません"
                )
            raise HTTPException(
                status_code=response.status_code,
                detail=f"ファイルの取得に失敗しました: {response.text}"
            )
            
        return response.json()
        
    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"予期せぬエラーが発生しました: {str(e)}"
        ) 