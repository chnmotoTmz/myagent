"""
LINE Webhookリクエストをシミュレートするテスト
"""
import pytest
import json
import os
import asyncio
import shutil
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import hashlib
import hmac
import base64

# プロジェクトルートをパスに追加してインポートできるようにする
sys.path.append(str(Path(__file__).parent.parent.parent))
# テスト対象のアプリケーション
from line_webhook.app.main import app
from line_webhook.app.summarizer import summarizer

# テスト用のクライアント
client = TestClient(app)

# テスト用の設定
TEST_USER_ID = "test_line_user_123"
TEST_CHANNEL_SECRET = "test_channel_secret"
TEST_ENDPOINT = "/api/webhook/line"

def generate_signature(body, channel_secret):
    """
    LINEのリクエスト署名を生成する
    """
    hash = hmac.new(
        channel_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return base64.b64encode(hash).decode('utf-8')

def setup_module():
    """
    テストモジュールの初期化
    """
    # テスト用のストレージディレクトリを作成
    os.makedirs("storage/test_webhook", exist_ok=True)

def teardown_module():
    """
    テストモジュールの終了時の処理
    """
    # テスト用のストレージディレクトリを削除
    if os.path.exists("storage/test_webhook"):
        shutil.rmtree("storage/test_webhook")

@pytest.fixture
def mock_line_api():
    """
    LINE APIモックを作成する
    """
    with patch("linebot.LineBotApi") as mock_line_bot_api, \
         patch("linebot.WebhookHandler") as mock_handler, \
         patch.dict(os.environ, {"LINE_CHANNEL_SECRET": TEST_CHANNEL_SECRET}):
        
        # イベントハンドラの設定
        mock_handler_instance = mock_handler.return_value
        
        # メッセージコンテンツの取得をモック
        mock_bot_instance = mock_line_bot_api.return_value
        content_mock = MagicMock()
        content_mock.content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00' # ダミーJPEGデータ
        mock_bot_instance.get_message_content.return_value = content_mock
        
        yield mock_bot_instance, mock_handler_instance

def test_line_webhook_text_message(mock_line_api):
    """
    テキストメッセージWebhookのテスト
    """
    # LINEイベントのペイロードを作成
    line_event = {
        "destination": "xxxxxxxxxx", 
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "123456789",
                    "text": "これはテストメッセージです。LINE Webhookのテスト中です。"
                },
                "timestamp": 1462629479859,
                "source": {
                    "type": "user",
                    "userId": TEST_USER_ID
                },
                "replyToken": "test_reply_token",
                "mode": "active"
            }
        ]
    }
    
    # リクエストボディを文字列化
    body = json.dumps(line_event)
    
    # 署名を生成
    signature = generate_signature(body, TEST_CHANNEL_SECRET)
    
    # モックの設定
    mock_bot_instance, mock_handler_instance = mock_line_api
    
    with patch("linebot.WebhookHandler.handle") as mock_handle, \
         patch("asyncio.create_task") as mock_create_task, \
         patch.object(summarizer, "create_summary", return_value={"summary": "テスト要約"}):
        
        # リクエスト送信
        response = client.post(
            TEST_ENDPOINT, 
            data=body,
            headers={"X-Line-Signature": signature}
        )
        
        # レスポンス検証
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # handler.handle メソッドが呼ばれたことを確認
        mock_handle.assert_called_once()
        
        # 要約機能が正しく呼び出されることを期待
        # 注: 実際のテストでは、summarizer.create_summaryの呼び出しを検証するが、
        # LINEイベントハンドラが非同期で動作するため完全な検証は難しい

def test_line_webhook_image_message(mock_line_api):
    """
    画像メッセージWebhookのテスト
    """
    # LINEイベントのペイロードを作成
    line_event = {
        "destination": "xxxxxxxxxx", 
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "image",
                    "id": "123456790",
                },
                "timestamp": 1462629479859,
                "source": {
                    "type": "user",
                    "userId": TEST_USER_ID
                },
                "replyToken": "test_reply_token",
                "mode": "active"
            }
        ]
    }
    
    # リクエストボディを文字列化
    body = json.dumps(line_event)
    
    # 署名を生成
    signature = generate_signature(body, TEST_CHANNEL_SECRET)
    
    # モックの設定
    mock_bot_instance, mock_handler_instance = mock_line_api
    
    with patch("linebot.WebhookHandler.handle") as mock_handle, \
         patch("asyncio.create_task") as mock_create_task, \
         patch.object(summarizer, "create_summary", return_value={"summary": "テスト画像要約"}):
        
        # リクエスト送信
        response = client.post(
            TEST_ENDPOINT, 
            data=body,
            headers={"X-Line-Signature": signature}
        )
        
        # レスポンス検証
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # handler.handle メソッドが呼ばれたことを確認
        mock_handle.assert_called_once()

def test_line_webhook_missing_signature():
    """
    署名がないリクエストのテスト（エラーになるべき）
    """
    line_event = {
        "destination": "xxxxxxxxxx", 
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "123456789",
                    "text": "署名のないリクエスト"
                },
                "source": {
                    "type": "user",
                    "userId": TEST_USER_ID
                }
            }
        ]
    }
    
    # 署名なしでリクエスト送信
    response = client.post(
        TEST_ENDPOINT, 
        json=line_event,
    )
    
    # 署名がないため400エラーになることを確認
    assert response.status_code == 400
    assert "Missing X-Line-Signature" in response.text

def test_line_webhook_invalid_signature():
    """
    不正な署名のリクエストのテスト
    """
    line_event = {
        "destination": "xxxxxxxxxx", 
        "events": [
            {
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "123456789",
                    "text": "不正な署名のリクエスト"
                },
                "source": {
                    "type": "user",
                    "userId": TEST_USER_ID
                }
            }
        ]
    }
    
    body = json.dumps(line_event)
    
    # 不正な署名でリクエスト送信
    response = client.post(
        TEST_ENDPOINT, 
        data=body,
        headers={"X-Line-Signature": "invalid_signature"}
    )
    
    # 署名が不正なため400エラーになることを確認
    assert response.status_code == 400
    assert "Invalid signature" in response.text

def test_get_summaries_api():
    """
    要約取得APIのテスト
    """
    # テスト用のサマリーデータを作成
    test_summary = {
        "user_id": TEST_USER_ID,
        "message_type": "text",
        "summary": "テスト要約内容",
        "timestamp": "2025-05-02T08:00:00.000000",
        "filepath": None
    }
    
    with patch.object(
        summarizer, 
        "get_recent_summaries", 
        return_value=[test_summary]
    ):
        # 要約取得APIを呼び出し
        response = client.get(f"/api/summaries/{TEST_USER_ID}")
        
        # レスポンスを検証
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert len(data["summaries"]) == 1
        assert data["summaries"][0]["summary"] == "テスト要約内容"