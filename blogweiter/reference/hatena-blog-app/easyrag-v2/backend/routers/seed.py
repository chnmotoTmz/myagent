from fastapi import APIRouter, HTTPException
import logging
import os
from services.content_processor import ContentProcessor

logger = logging.getLogger(__name__)
router = APIRouter()

# APIキーを取得
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
content_processor = ContentProcessor(api_token=OPENAI_API_KEY)

@router.post("")
async def generate_seed(request: dict):
    """種記事を生成するエンドポイント"""
    try:
        logger.info("種記事生成開始")
        logger.info(f"リクエスト: {request}")

        if not request.get('messages'):
            raise HTTPException(status_code=400, detail="メッセージが必要です")

        messages = request['messages']
        
        # テキストと画像の内容を収集
        contents = []
        for msg in messages:
            if msg['type'] == 'text':
                contents.append(msg['content'])
            elif msg['type'] == 'image':
                contents.append(f"[画像: {msg['content']}]")

        if not contents:
            raise HTTPException(status_code=400, detail="テキストまたは画像が必要です")

        raw_content = "\n".join(contents)
        logger.info(f"元のテキスト: {raw_content}")

        try:
            generated_content = await content_processor.generate_seed_article(raw_content)
            logger.info(f"生成されたテキスト: {generated_content}")
            
            if not generated_content:
                raise Exception("生成された記事が空です")

            return {"content": generated_content}

        except Exception as e:
            logger.error(f"記事生成処理エラー: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"種記事生成エラー: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 