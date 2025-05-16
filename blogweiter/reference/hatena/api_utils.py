import requests
import json
import os
import re
from collections import Counter
import logging
from http.client import HTTPConnection
import pdb

# ロギングの設定
def setup_logging():
    # ルートロガーの設定
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # requestsとurllibのロガーを設定
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    
    # HTTP接続のデバッグログを有効化
    HTTPConnection.debuglevel = 1

def log_request(response):
    logger = logging.getLogger(__name__)
    logger.debug(f"Request URL: {response.request.url}")
    logger.debug(f"Request method: {response.request.method}")
    
    # リクエストヘッダーから Content-Type のみを記録
    content_type = response.request.headers.get('Content-Type', 'Not specified')
    logger.debug(f"Request Content-Type: {content_type}")
    
    # リクエストボディは長さのみを記録
    body_length = len(response.request.body) if response.request.body else 0
    logger.debug(f"Request body length: {body_length}")
    
    logger.debug(f"Response status: {response.status_code}")
    
    # レスポンスヘッダーから Content-Type のみを記録
    content_type = response.headers.get('Content-Type', 'Not specified')
    logger.debug(f"Response Content-Type: {content_type}")
    
    # レスポンスの内容は長さのみを記録
    content_length = len(response.text) if response.text else 0
    logger.debug(f"Response content length: {content_length}")

def assign_role(message):
    """Automatically assign a role to the message based on its content using advanced rules and scoring."""
    
    roles = ["USER", "CHATBOT", "SYSTEM", "TOOL"]
    scores = {role: 0 for role in roles}

    # Define keywords for each role
    keywords = {
        "USER": ["お願い", "質問", "教えて", "どうすれば", "なぜ", "ユーザー", "知りたい", "方法", "やり方", "困っている", "問題", "ヘルプ"],
        "CHATBOT": ["こんにちは", "ありがとう", "どういたしまして", "会話", "はい", "いいえ", "確認", "了解", "かしこまりました"],
        "SYSTEM": ["設定", "システム", "エラー", "指示", "操作", "システムメッセージ", "完了", "状態", "バージョン", "アップデート"],
        "TOOL": ["検索", "ツール", "データ", "API", "計算", "解析", "処理", "分析", "変換", "生成", "抽出", "翻訳"]
    }

    # Count keyword occurrences
    words = message.lower().split()
    word_counter = Counter(words)
    
    # Calculate scores based on keyword occurrence
    for role, role_keywords in keywords.items():
        scores[role] = sum(word_counter[word] for word in role_keywords if word in word_counter)

    # Additional context-based scoring
    if "エラー" in message or "システム" in message:
        scores["SYSTEM"] += 2
    if "検索" in message or "ツール" in message:
        scores["TOOL"] += 2
    if "ありがとう" in message or message.strip() in ["はい", "いいえ", "了解"]:
        scores["CHATBOT"] += 2
    if any(keyword in message for keyword in ["お願い", "教えて", "質問"]):
        scores["USER"] += 2

    # Determine the role with the highest score
    assigned_role = max(scores, key=scores.get)

    # If no significant keywords are found, default to "USER"
    if all(score == 0 for score in scores.values()):
        assigned_role = "USER"

    return assigned_role


    
def summarize_chat_history_google(chat_history, api_key):
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
    headers = {'Content-Type': 'application/json'}
    
    history_text = "\n".join([f"{msg['role']}: {msg['message']}" for msg in chat_history])
    
    prompt = f"以下のチャット履歴を簡潔に要約してください：\n\n{history_text}"
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    params = {'key': api_key}

    try:
        response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
        log_request(response)  # ログを記録
        response.raise_for_status()
        result = response.json()
        
        logging.debug(f"API Response: {result}")  # APIレスポンス全体をログに記録
        
        if 'candidates' in result and result['candidates']:
            candidate = result['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                for part in candidate['content']['parts']:
                    if 'text' in part:
                        return part['text']
            
            logging.error(f"Unexpected response structure: {candidate}")
            return "Error: Unexpected response structure"
        else:
            logging.error(f"No candidates in API response: {result}")
            return "Error: No valid response from API"
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error in summarize_chat_history_google: {str(e)}")
        return "Error: Failed to parse API response"
    except KeyError as e:
        logging.error(f"KeyError in summarize_chat_history_google: {str(e)}")
        logging.error(f"API Response causing KeyError: {result}")
        return f"Error: Unexpected response structure - missing key {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error in summarize_chat_history_google: {str(e)}")
        return f"Error: An unexpected error occurred"
    except requests.RequestException as e:
        logging.error(f"Request error in summarize_chat_history_google: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response status code: {e.response.status_code}")
            logging.error(f"Response content (first 200 chars): {e.response.text[:200]}")
        return f"Error: {str(e)}"
   

def generate_response(chat_history, message, google_api_key, cohere_api_key):
    """
    まずGoogleのAPIを使用して応答を生成し、失敗した場合やレスポンスが不十分な場合はCohereにフォールバックする
    """
    google_response, updated_history = generate_response_google(chat_history, message, google_api_key)
    
    if is_response_adequate(google_response):
        return google_response, updated_history
    else:
        logging.info("Google APIの応答が不十分です。Cohereにフォールバックします。")
        cohere_response, updated_history = generate_response_cohere(chat_history, message, cohere_api_key,google_api_key)
        return cohere_response, updated_history

def is_response_adequate(response):
    """
    応答が適切かどうかを判断する
    この関数は必要に応じて拡張できます
    """
    if response.startswith("Error:"):
        return False
    if len(response.split()) < 10:  # 例: 応答が10単語未満の場合は不十分とみなす
        return False
    return True

def generate_response_google(chat_history, message, api_key):

    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
    headers = {'Content-Type': 'application/json'}

    history_summary = summarize_chat_history_google(chat_history, api_key)
    last_turn = chat_history[-1] if chat_history else {"role": "SYSTEM", "message": "This is the start of the conversation."}

    prompt = f"""
    これは以前の会話の要約です: {history_summary}
    
    最後のメッセージ:
    {last_turn['role']}: {last_turn['message']}
    
    新しいメッセージ:
    {assign_role(message)}: {message}
    
    上記の文脈を考慮して適切な応答を生成してください。
    """

    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    params = {'key': api_key}

    pdb.set_trace()

    try:
        response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
        log_request(response)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' in result and result['candidates']:
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
        else:
            generated_text = "Error: Unable to generate response"

        updated_history = [
            {"role": "SYSTEM", "message": f"これは以前の会話の要約です: {history_summary}"},
            {"role": assign_role(message), "message": message},
            {"role": "CHATBOT", "message": generated_text}
        ]
        
        return generated_text, updated_history
    except Exception as e:
        logging.error(f"Error in generate_response_google: {str(e)}")
        return f"Error: {str(e)}", chat_history

def generate_response_cohere(chat_history, message, api_key,google_api_key):
    url = "https://api.cohere.ai/v1/chat"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": api_key
    }

    history_summary = summarize_chat_history_google(chat_history, google_api_key)
    last_turn = chat_history[-1] if chat_history else {"role": "SYSTEM", "message": "This is the start of the conversation."}
    
    prepared_history = [
        {"role": "SYSTEM", "message": f"これは以前の会話の要約です: {history_summary}"},
        last_turn,
        {"role": assign_role(message), "message": message}
    ]

    data = {
        "chat_history": prepared_history,
        "message": message,
        "connectors": [{"id": "web-search"}]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        log_request(response)
        response.raise_for_status()
        response_data = response.json()
        generated_text = response_data.get('text', "Error: No 'text' key found in the API response.")
        
        updated_history = [
            {"role": "SYSTEM", "message": f"これは以前の会話の要約です: {history_summary}"},
            {"role": assign_role(message), "message": message},
            {"role": "CHATBOT", "message": generated_text}
        ]
        
        return generated_text, updated_history
    except Exception as e:
        logging.error(f"Error in generate_response_cohere: {str(e)}")
        return f"Error: {str(e)}", chat_history


if __name__ == "__main__":
    setup_logging()  # ロギングをセットアップ
    chat_history = [
        {"role": "USER", "message": "こんにちは、天気について教えてください。"},
        {"role": "CHATBOT", "message": "はい、どの地域の天気をお知りになりたいですか？"}
    ]
    message = "東京の天気を教えてください。"
    google_api_key = os.getenv("GOOGLE_API_KEY")
    response = generate_response_cohere(chat_history, message, google_api_key)
    print(response)

