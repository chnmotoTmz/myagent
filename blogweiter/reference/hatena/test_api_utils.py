import os
from dotenv import load_dotenv
import pytest
from api_utils import generate_response_cohere,generate_response_gemini
import re

load_dotenv()  # 環境変数を読み込む

# APIキーが設定されているか確認
API_TOKEN_1 = os.getenv("API_TOKEN_1")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

def log_request(url, headers, data):
    pass

# Geminiのテスト
@pytest.mark.skipif(not API_TOKEN_1, reason="API_TOKEN_1 is not set")
def test_generate_response_gemini():
    prompt = "今日の天気は？"
    response = generate_response_gemini(prompt, API_TOKEN_1)
    assert isinstance(response, str)  # 応答が文字列であることを確認
    assert len(response) > 0  # 応答が空でないことを確認

# Cohereのテスト
@pytest.mark.skipif(not COHERE_API_KEY, reason="COHERE_API_KEY is not set")
def test_generate_response_cohere():
    chat_history = [{"role": "USER", "message": "こんにちは"}]
    message = "元気ですか？"
    response = generate_response_cohere(chat_history, message)
    assert isinstance(response, str)  # 応答が文字列であることを確認
    assert len(response) > 0  # 応答が空でないことを確認

@pytest.mark.skipif(not API_TOKEN_1, reason="API_TOKEN_1 is not set")
def test_generate_response_gemini_with_role():
    prompt = "今日の天気は？"
    role = "気象予報士"
    # role引数を渡さずに呼び出す
    response = generate_response_gemini(prompt, API_TOKEN_1) 
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.skipif(not COHERE_API_KEY, reason="COHERE_API_KEY is not set")
def test_generate_response_cohere_with_role():
    chat_history = [{"role": "USER", "message": "こんにちは"}]
    message = "具合が悪いのですが…"
    role = "医者"

    print(f"--- test_generate_response_cohere_with_role ---")  # テスト関数の開始ログ
    print(f"  chat_history: {chat_history}")
    print(f"  message: {message}")
    print(f"  role: {role}")

    response = generate_response_cohere(chat_history, message, role=role)

    print(f"  response: {response}")  # レスポンスのログ
    print("---------------------------------------------")  # テスト関数の終了ログ

    assert isinstance(response, str)
    assert len(response) > 0
    assert any(keyword in response for keyword in ["症状", "診察", "治療", "病院"])

import pytest
from api_utils import assign_role

# assign_role() の単体テスト
@pytest.mark.parametrize(
    "message, expected_role",
    [
        ("システムエラーが発生しました", "System"),
        ("最新のニュース記事を検索してください", "Tool"),
        ("こんにちは", "Chatbot"),
        ("今日の天気は？", "User"),
        ("ありがとう", "Chatbot"),
        ("使い方を教えてください", "User"),
        ("設定を変更したい", "User"),
        ("データを分析してください", "User"),
        ("おはよう", "User"),
        ("こんばんは", "Chatbot"),
        ("", "User"),  # 空文字列の場合はUserになることを確認
    ],
)
def test_assign_role(message, expected_role):
    actual_role = assign_role(message)
    assert actual_role == expected_role, f"Expected role '{expected_role}' for message '{message}', but got '{actual_role}'"