import os
import base64
import io
from PIL import Image
import requests
import json
from typing import List, Optional, Dict
from datetime import datetime
from dotenv import load_dotenv
from .simple_search_service import SimpleSearchService
import logging
import time


logger = logging.getLogger(__name__)

class ContentProcessor:
    def __init__(self, api_token: str):
        # API_TOKEN_1を使用
        load_dotenv()
        self.api_token_gemini = os.getenv("API_TOKEN_1")
        if not self.api_token_gemini:
            raise ValueError("API_TOKEN_1が設定されていません")
              
        self.logger = logging.getLogger(__name__)

    def generate_response(self, prompt: str, max_retries=3, initial_delay=1):
        """テキストからレスポンスを生成"""
        url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        params = {'key': self.api_token_gemini}

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, params=params, json=data)
                response.raise_for_status()
                result = response.json()
                
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0].get('text', "")
                return ""
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    logger.warning(f"リトライ {attempt + 1}/{max_retries}... {delay}秒後")
                    time.sleep(delay)
                else:
                    raise Exception(f"API呼び出しに失敗: {str(e)}")
        
        raise Exception("最大リトライ回数に達しました")

    def generate_response_with_image(self, prompt: str, encoded_image: str, max_retries=3, initial_delay=1):
        """画像付きでレスポンスを生成"""
        url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": encoded_image
                        }
                    }
                ]
            }]
        }
        params = {'key': self.api_token_gemini}

        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, params=params, json=data)
                response.raise_for_status()
                result = response.json()
                
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0].get('text', "")
                return ""
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    logger.warning(f"リトライ {attempt + 1}/{max_retries}... {delay}秒後")
                    time.sleep(delay)
                else:
                    raise Exception(f"API呼び出しに失敗: {str(e)}")
        
        raise Exception("最大リトライ回数に達しました")

    async def process_image(self, image_path: str) -> str:
        """画像をテキストに変換"""
        try:
            with Image.open(image_path) as img:
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG")
                encoded_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
                
                prompt = "この画像の内容を詳しく説明してください。"
                url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
                
                headers = {'Content-Type': 'application/json'}
                data = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": encoded_image
                                }
                            }
                        ]
                    }]
                }
                params = {'key': self.api_token_gemini}
                
                response = requests.post(url, headers=headers, params=params, json=data)
                response.raise_for_status()
                result = response.json()
                
                if 'candidates' in result and result['candidates']:
                    return result['candidates'][0]['content']['parts'][0].get('text', "")
                return ""
                
        except Exception as e:
            print(f"Error processing image: {e}")
            return ""

    async def generate_seed_article(self, content: str, references: list = None) -> str:
        """種記事を生成

        Args:
            content: テキストメッセージまたは画像ID
            references: 追加の参照情報（オプション）

        Returns:
            str: RAG検索用の簡潔な状況説明
        """
        try:
            # テキストコンテンツを優先
            if not content.startswith('[画像:'):
                prompt = f"""
                以下の内容から、重要なポイントを抽出し、簡潔な状況説明を生成してください。
                装飾的な文章は避け、事実と意図を明確に示してください。
                
                入力内容:
                {content}
                
                出力形式:
                - 重要な事実のみを箇条書きで
                - 場所、時間、目的などの具体的な情報を含める
                - 主観的な感想は除外する
                - 200字以内に収める
                - 元々のテキストは、そのままコピペとして採用して
                """
                return self.generate_response(prompt)
            
            # 画像の場合は補足情報として扱う
            else:
                image_id = content.split('[画像:')[1].split(']')[0].strip()
                logger.info(f"画像ID: {image_id}")
                
                image_response = requests.get(
                    f"{os.getenv('NAS_API_URL')}/image/{image_id}",
                    headers={'X-API-Key': os.getenv('NAS_API_KEY')}
                )
                if not image_response.ok:
                    raise Exception("画像の取得に失敗しました")
                
                encoded_image = base64.b64encode(image_response.content).decode('utf-8')
                
                prompt = """
                この画像から、以下の情報を抽出してください：
                - 場所や環境
                - 写っているもの
                - 時間帯や季節の特徴
                - レシートの場合は家計簿用に緻密に読み取って
                装飾的な説明は避け、事実のみを簡潔に列挙してください。
                """
                return self.generate_response_with_image(prompt, encoded_image)
                
        except Exception as e:
            logger.error(f"種記事生成エラー: {str(e)}")
            raise Exception(f"種記事生成に失敗しました: {str(e)}")

    async def process_image_data(self, image_data: bytes) -> Optional[str]:
        """画像の説明文を生成"""
        try:
            # 画像処理ロジックを実装
            # 仮の実装として、固定の説明文を返す
            return "画像の説明文"
        except Exception as e:
            self.logger.error(f"画像処理エラー: {str(e)}")
            return None

    async def generate_full_article(
        self,
        seed_article: str,
        similar_articles: List[Dict]
    ) -> str:
        """完全な記事を生成"""
        try:
            self.logger.info("記事生成開始")
            self.logger.info(f"Seed article length: {len(seed_article)}")
            self.logger.info(f"Similar articles count: {len(similar_articles)}")

            prompt = f"""
            以下の内容からブログ記事を生成してください。
            - 2000字程度の記事
            - 口語を参考記事に合わせた文体とする
            - 具体的な経験や感想を含める
            - 参考記事の情報を適切に引用
            - 画像生成用プロンプトの最後に "miniature" を含めること

            出力形式:形式はマークダウンで

            元の内容:
            {seed_article}

            参考記事:
            {json.dumps(similar_articles, ensure_ascii=False, indent=2)}


 
            """

            result = self.generate_response(prompt)
            return result

        except Exception as e:
            self.logger.error(f"記事生成エラー: {str(e)}")
            raise 