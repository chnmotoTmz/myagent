import logging
from typing import List, Optional, Dict
from datetime import datetime
import httpx
from enum import Enum
import os
from urllib.parse import quote
from services.hatena_service import HatenaService

logger = logging.getLogger(__name__)

class ContentDomain(str, Enum):
    MOUNTAIN = "mountain"
    LIFEHACK = "lifehack"
    LANGUAGE = "language"

class Message:
    def __init__(self, id, type, timestamp, content):
        self.id = id
        self.type = type
        self.timestamp = timestamp
        self.content = content

    def get_preview(self):
        """メッセージのプレビューを生成"""
        return f"{self.timestamp} - {self.content[:30]}..."

class ContentGenerator:
    def __init__(self, webhook_base_url: str, api_key: str):
        self.webhook_base_url = webhook_base_url
        self.api_key = api_key
        
        print("ContentGenerator初期化時の設定値:")
        print(f"WEBHOOK_BASE_URL: {self.webhook_base_url}")
        print(f"API_KEY: {self.api_key}")
        
        self.headers = {
            "accept": "application/json",
            "X-API-Key": self.api_key
        }
        self.messages = []

    async def get_messages_list(self) -> List[dict]:
        """メッセージリストを取得"""
        try:
            # ファイル一覧を取得
            files_response = await self._make_request("/files")
            if not files_response:
                return []

            messages = []
            for file_info in files_response:
                file_path = file_info.get("path")
                if not file_path:
                    continue

                # 各ファイルのメッセージを取得
                message_response = await self._make_request(f"/file/{file_path}")
                if not message_response:
                    continue

                # レスポンスがリスト形式の場合、各メッセージを処理
                if isinstance(message_response, list):
                    for msg in message_response:
                        try:
                            messages.append({
                                "id": msg.get("message_id", ""),
                                "type": msg.get("type", ""),
                                "timestamp": datetime.fromisoformat(msg.get("timestamp", "")),
                                "content": msg.get("content", "")
                            })
                        except Exception as e:
                            print(f"メッセージの処理に失敗: {file_path} - {str(e)}")
                            continue

            return messages

        except Exception as e:
            print(f"メッセージリストの取得に失敗: {str(e)}")
            return []

    async def get_message(self, message_id: str) -> Optional[dict]:
        """個別のメッセージを取得"""
        try:
            # ファイル一覧を取得
            files_response = await self._make_request("/files")
            if not files_response:
                return None

            # ファイルのパスを見つける
            file_path = None
            for file_info in files_response:
                if message_id in file_info.get("path", ""):
                    file_path = file_info["path"]
                    break

            if not file_path:
                return None

            # メッセージの内容を取得
            message_response = await self._make_request(f"/file/{file_path}")
            if not message_response:
                return None

            # レスポンスがリスト形式の場合、最初のメッセージを返す
            if isinstance(message_response, list):
                # リストが空でないことを確認
                if message_response:
                    return {
                        "id": message_response[0].get("message_id", ""),
                        "type": message_response[0].get("type", ""),
                        "timestamp": datetime.fromisoformat(message_response[0].get("timestamp", "")),
                        "content": message_response[0].get("content", "")
                    }
            return None

        except Exception as e:
            print(f"メッセージの取得に失敗: {message_id} - {str(e)}")
            return None

    async def generate_article(self, message_id: str) -> str:
        """記事を生成"""
        try:
            message = await self.get_message(message_id)
            if not message:
                raise ValueError("メッセージが見つかりません")
            
            # ドメインを判定して記事を生成
            content = message["content"]
            domain = self.detect_domain(content)
            
            return f"【{domain}】について\n\n{content}"
        except Exception as e:
            raise Exception(f"記事生成に失敗: {str(e)}")

    def detect_domain(self, content: str) -> ContentDomain:
        """コンテンツのドメインを判定"""
        keywords = {
            ContentDomain.MOUNTAIN: ["山", "ハイキング", "登山", "アウトドア"],
            ContentDomain.LIFEHACK: ["効率", "工夫", "時短", "整理"],
            ContentDomain.LANGUAGE: ["英語", "学習", "語学", "勉強"]
        }
        
        scores = {domain: 0 for domain in ContentDomain}
        for domain, words in keywords.items():
            scores[domain] = sum(1 for word in words if word in content)
            
        return max(scores.items(), key=lambda x: x[1])[0]

    async def generate_seed_content(self, message_id: str):
        """種記事の生成"""
        message = await self.get_message(message_id)
        domain = self.detect_domain(message.get("content", ""))
        
        return {
            "content": message.get("content", ""),
            "domain": domain,
            "images": message.get("images", []),
            "timestamp": message.get("timestamp"),
            "message_id": message_id
        }

    def generate_content(self, template, content):
        """コンテンツを生成"""
        # AIを使用したコンテンツ生成ロジックを実装
        pass 

    async def _make_request(self, path: str):
        """APIリクエストを行い、レスポンスを返す"""
        try:
            async with httpx.AsyncClient(verify=False) as client:
                # リクエストの詳細をログ出力
                print("リクエストURL:", f"{self.webhook_base_url}{path}")
                print("リクエストヘッダー:", self.headers)
                
                response = await client.get(
                    f"{self.webhook_base_url}{path}",
                    headers=self.headers,
                    timeout=30.0
                )
                
                # レスポンスの詳細をログ出力
                print("レスポンスステータス:", response.status_code)
                print("レスポンスヘッダー:", dict(response.headers))
                
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"エラーの詳細: {str(e)}")
            return None 

    async def get_hatena_entries(self) -> List[Dict]:
        """はてなブログの記事を取得"""
        try:
            # はてなブログサービスのインスタンスを作成
            hatena_service = HatenaService(
                hatena_id=os.getenv("HATENA_ID"),
                blog_domain=os.getenv("BLOG_DOMAIN"),
                api_key=os.getenv("HATENA_API_KEY")
            )

            # 記事を取得
            entries = hatena_service.get_entries()
            
            # 検索用に整形
            formatted_entries = []
            for entry in entries:
                formatted_entries.append({
                    "title": entry.get("title", ""),
                    "text_content": entry.get("text_content", ""),
                    "url": entry.get("url", ""),
                    "updated": entry.get("updated", "")
                })

            return formatted_entries

        except Exception as e:
            logger.error(f"はてなブログ記事の取得エラー: {str(e)}")
            return [] 