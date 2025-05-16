from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from services.simple_search_service import SimpleSearchService

logger = logging.getLogger(__name__)
router = APIRouter()
search_service = SimpleSearchService()

class SearchRequest(BaseModel):
    query: str
    top_n: Optional[int] = 5

@router.post("/analyze")
async def analyze_content(request: SearchRequest):
    """RAG検索を実行するエンドポイント"""
    try:
        logger.info(f"検索クエリ: {request.query}")
        logger.info(f"取得件数: {request.top_n}")

        # 検索を実行
        results = await search_service.search(
            query=request.query,
            top_n=request.top_n
        )
        
        return {
            "results": results
        }
        
    except Exception as e:
        logger.error(f"RAG検索エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 