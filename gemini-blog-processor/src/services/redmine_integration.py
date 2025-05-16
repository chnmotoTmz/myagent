"""
Redmine連携用のサービスクラス
Redmineチケット管理エージェントのAPIと連携して、メッセージの転送やコマンド処理を行う
"""

import json
import time
import logging
import requests
from typing import Dict, Any, Optional, Union, List
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from .. import config

class RedmineIntegrationService:
    """Redmineチケット管理エージェントと連携するためのサービスクラス"""
    
    def __init__(self):
        """サービスの初期化"""
        self.api_url = config.REDMINE_API_URL
        self.api_key = config.REDMINE_API_KEY
        self.logger = logging.getLogger(__name__)
        
        # セッションの設定（コネクション再利用のため）
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,  # リトライ回数
            backoff_factor=1,  # 指数バックオフ係数
            status_forcelist=[429, 500, 502, 503, 504],  # リトライするステータスコード
            allowed_methods=["POST", "GET"]  # リトライを許可するHTTPメソッド
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def forward_message(self, user_id: str, message_text: str, 
                       intent_data: Optional[Dict[str, Any]] = None,
                       source_type: str = "user",
                       reply_token: Optional[str] = None) -> Dict[str, Any]:
        """
        メッセージをRedmineチケット管理エージェントに転送する
        
        Args:
            user_id: LINEユーザーID
            message_text: メッセージ本文
            intent_data: 投稿意図分析データ（オプション）
            source_type: メッセージのソースタイプ（user/group/room）
            reply_token: LINEのリプライトークン（オプション）
            
        Returns:
            Dict[str, Any]: APIレスポンス（JSON）
        """
        # リクエストデータの構築
        request_data = {
            "user_id": user_id,
            "message_text": message_text,
            "timestamp": int(time.time()),
            "source_type": source_type
        }
        
        # 投稿意図分析データがある場合は追加
        if intent_data:
            request_data["intent_data"] = intent_data
            
        # リプライトークンがある場合は追加
        if reply_token:
            request_data["reply_token"] = reply_token
            
        # リクエストヘッダーの設定
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        
        try:
            # APIリクエストの送信
            response = self.session.post(
                f"{self.api_url}/api/receive_message",
                headers=headers,
                json=request_data,
                timeout=30  # タイムアウト設定（30秒）
            )
            
            # レスポンスのステータスコードによる処理
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 202:  # 非同期処理が開始された
                result = response.json()
                self.logger.info(f"非同期処理が開始されました: {result.get('process_id')}")
                return result
            elif response.status_code == 400:
                self.logger.error(f"リクエスト形式が不正です: {response.text}")
                return {"status": "error", "message": "リクエスト形式が不正です", "error_code": "bad_request"}
            elif response.status_code == 401:
                self.logger.error(f"認証エラー: {response.text}")
                return {"status": "error", "message": "APIキーが無効です", "error_code": "unauthorized"}
            elif response.status_code == 429:
                self.logger.error(f"リクエスト制限超過: {response.text}")
                return {"status": "error", "message": "リクエスト制限を超過しました", "error_code": "rate_limit"}
            else:
                self.logger.error(f"APIエラー ({response.status_code}): {response.text}")
                return {"status": "error", "message": f"APIエラー ({response.status_code})", "error_code": "api_error"}
                
        except requests.exceptions.Timeout:
            self.logger.error("APIリクエストがタイムアウトしました")
            return {"status": "error", "message": "リクエストがタイムアウトしました", "error_code": "timeout"}
        except requests.exceptions.ConnectionError:
            self.logger.error("APIサーバーに接続できませんでした")
            return {"status": "error", "message": "サーバーに接続できませんでした", "error_code": "connection_error"}
        except Exception as e:
            self.logger.error(f"APIリクエスト中にエラーが発生しました: {str(e)}")
            return {"status": "error", "message": f"エラーが発生しました: {str(e)}", "error_code": "unknown_error"}
    
    def check_process_status(self, process_id: str) -> Dict[str, Any]:
        """
        非同期処理の状態を確認する
        
        Args:
            process_id: 処理ID
            
        Returns:
            Dict[str, Any]: 処理状態（JSON）
        """
        headers = {
            "X-API-Key": self.api_key
        }
        
        try:
            response = self.session.get(
                f"{self.api_url}/api/status/{process_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"ステータス確認エラー ({response.status_code}): {response.text}")
                return {"status": "error", "message": f"ステータス確認エラー ({response.status_code})"}
                
        except Exception as e:
            self.logger.error(f"ステータス確認中にエラーが発生しました: {str(e)}")
            return {"status": "error", "message": f"エラーが発生しました: {str(e)}"}
    
    def process_message_with_intent(self, user_id: str, message_text: str, 
                                   intent_type: str, confidence_score: float,
                                   keywords: List[str], source_type: str = "user",
                                   reply_token: Optional[str] = None) -> Dict[str, Any]:
        """
        投稿意図分析結果を含めてメッセージを処理する
        
        Args:
            user_id: LINEユーザーID
            message_text: メッセージ本文
            intent_type: 意図タイプ
            confidence_score: 確信度スコア
            keywords: 関連キーワードリスト
            source_type: メッセージのソースタイプ（user/group/room）
            reply_token: LINEのリプライトークン（オプション）
            
        Returns:
            Dict[str, Any]: APIレスポンス（JSON）
        """
        # 投稿意図分析データの作成
        intent_data = {
            "intent_type": intent_type,
            "confidence_score": confidence_score,
            "keywords": keywords
        }
        
        # メッセージ転送
        return self.forward_message(
            user_id=user_id,
            message_text=message_text,
            intent_data=intent_data,
            source_type=source_type,
            reply_token=reply_token
        )
    
    def is_command_message(self, message_text: str) -> bool:
        """
        メッセージがコマンドかどうかを判定する
        
        Args:
            message_text: メッセージ本文
            
        Returns:
            bool: コマンドの場合はTrue
        """
        return message_text.startswith('@')
    
    def is_redmine_command(self, message_text: str) -> bool:
        """
        Redmineチケット管理エージェント宛のコマンドかどうかを判定する
        
        Args:
            message_text: メッセージ本文
            
        Returns:
            bool: Redmineコマンドの場合はTrue
        """
        redmine_commands = ['@help', '@create', '@list']
        command_parts = message_text.split()
        
        if not command_parts:
            return False
            
        command = command_parts[0].lower()
        return any(command.startswith(cmd.lower()) for cmd in redmine_commands)
    
    def is_gemini_command(self, message_text: str) -> bool:
        """
        Gemini Blog Processor宛のコマンドかどうかを判定する
        
        Args:
            message_text: メッセージ本文
            
        Returns:
            bool: Geminiコマンドの場合はTrue
        """
        gemini_commands = ['@g.today', '@g.tasks', '@g.log', '@g.summary']
        command_parts = message_text.split()
        
        if not command_parts:
            return False
            
        command = command_parts[0].lower()
        return any(command.startswith(cmd.lower()) for cmd in gemini_commands)
    
    def handle_redmine_command(self, user_id: str, message_text: str, 
                              source_type: str = "user",
                              reply_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Redmineチケット管理エージェント宛のコマンドを処理する
        
        Args:
            user_id: LINEユーザーID
            message_text: メッセージ本文（コマンド）
            source_type: メッセージのソースタイプ（user/group/room）
            reply_token: LINEのリプライトークン（オプション）
            
        Returns:
            Dict[str, Any]: APIレスポンス（JSON）
        """
        # コマンドはそのままRedmineチケット管理エージェントに転送
        return self.forward_message(
            user_id=user_id,
            message_text=message_text,
            source_type=source_type,
            reply_token=reply_token
        )
