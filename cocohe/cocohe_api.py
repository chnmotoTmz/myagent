from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import requests
import json
import os
from typing import Dict
import sqlite3
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel


app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class ChatRequest(BaseModel):
    topic: str
    message: str


class User(BaseModel):
    username: str
    hashed_password: str


@app.on_event("startup")
async def startup_event():
    create_connection()
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (username, hashed_password) VALUES (?, ?)", ("john", "password"))
    cursor.execute("INSERT OR IGNORE INTO users (username, hashed_password) VALUES (?, ?)", ("alice", "password"))
    conn.commit()
    conn.close()

    
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (form_data.username,))
    user = cursor.fetchone()
    conn.close()

    if user is None or not verify_password(form_data.password, user[2]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": user[1], "token_type": "bearer"}

def verify_password(plain_password, hashed_password):
    # ここでは、平文のパスワードとハッシュ化されたパスワードを比較する処理を行います。
    # 実際のアプリケーションでは、適切なパスワードハッシュアルゴリズムを使用してください。
    return plain_password == hashed_password


def create_connection():
    conn = None
    try:
        conn = sqlite3.connect("chat_history.db")
        print("Connected to SQLite")

        # usersテーブルを作成
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL
            )
        """)

        # chat_historyテーブルを作成
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        conn.commit()
    except sqlite3.Error as e:
        print(e)
    finally:
        if conn:
            conn.close()


def generate_content(chat_history, message):
    url = "https://api.cohere.ai/v1/chat"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": os.getenv("COHERE_API_KEY")
    }
    data = {
        "chat_history": chat_history,
        "message": message,
        "connectors": [{"id": "web-search"}]
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        try:
            response_data = response.json()
            if 'text' in response_data:
                return response_data['text']
            else:
                return "No 'text' key found in the API response."
        except json.JSONDecodeError:
            return "Failed to parse the API response as JSON."
    else:
        return f"Request failed with status code: {response.status_code}"



# ダミーのユーザーデータベース
user_db = {
    "john": {
        "username": "john",
        "hashed_password": "hashedjohnspassword",
    },
    "alice": {
        "username": "alice",
        "hashed_password": "hashedalicespassword",
    }
}

# ユーザーごとのトピックとチャット履歴を保持する辞書
chat_history_db: Dict[str, Dict[str, list]] = {}

def get_user(token: str = Depends(oauth2_scheme)):
    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (token,))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    return {"id": user[0], "username": user[1]}

@app.post("/chat")
async def chat(request: ChatRequest, user: dict = Depends(get_user)):
    user_id = user["id"]
    topic = request.topic
    message = request.message

    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, message FROM chat_history
        WHERE user_id = ? AND topic = ?
        ORDER BY id
    """, (user_id, topic))
    chat_history = [{"role": row[0], "message": row[1]} for row in cursor.fetchall()]

    response_message = generate_content(chat_history, message)

    cursor.execute("""
        INSERT INTO chat_history (user_id, topic, role, message)
        VALUES (?, ?, ?, ?)
    """, (user_id, topic, "USER", message))
    cursor.execute("""
        INSERT INTO chat_history (user_id, topic, role, message)
        VALUES (?, ?, ?, ?)
    """, (user_id, topic, "CHATBOT", response_message))

    conn.commit()
    conn.close()

    return {"message": response_message}

@app.post("/reset")
async def reset_chat_history(topic: str, user: dict = Depends(get_user)):
    user_id = user["id"]

    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM chat_history
        WHERE user_id = ? AND topic = ?
    """, (user_id, topic))

    conn.commit()
    conn.close()

    return {"message": "Chat history has been reset for the specified topic."}

@app.get("/chat_history")
async def get_chat_history(topic: str, user: dict = Depends(get_user)):
    user_id = user["id"]

    conn = sqlite3.connect("chat_history.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, message FROM chat_history
        WHERE user_id = ? AND topic = ?
        ORDER BY id
    """, (user_id, topic))
    chat_history = [{"role": row[0], "message": row[1]} for row in cursor.fetchall()]

    conn.close()

    return {"chat_history": chat_history}
    