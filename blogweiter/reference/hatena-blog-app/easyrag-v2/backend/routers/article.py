from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging
import os
from services.content_processor import ContentProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
content_processor = ContentProcessor(api_token=OPENAI_API_KEY)

class GenerateArticleRequest(BaseModel):
    seed: str
    references: List[dict]

@router.post("/generate-full")
async def generate_full_article(request: GenerateArticleRequest):
    """完全な記事を生成するエンドポイント"""
    try:
        if not request.seed:
            raise HTTPException(status_code=400, detail="種記事が必要です")
        
        result = await content_processor.generate_full_article(
            seed_article=request.seed,
            similar_articles=request.references
        )
        
        return {
            "title": "生成された記事",
            "content": result,
            "tags": ["自動生成", "ブログ"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 