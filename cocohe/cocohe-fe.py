import streamlit as st
import requests

# Streamlitアプリケーションの設定
st.set_page_config(page_title="Cohere AI Chat", page_icon=":robot_face:")

# サイドバーでユーザー認証トークンを入力
user_token = st.sidebar.text_input("User Authentication Token")

# トピックの選択または新規作成
topic = st.sidebar.text_input("Topic")

# チャット履歴を取得する関数
def get_chat_history():
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {"topic": topic}
    response = requests.get("http://localhost:8000/chat_history", headers=headers, params=params)

    if response.status_code == 200:
        return response.json()["chat_history"]
    else:
        st.error("Error occurred while fetching the chat history.")
        return []

# チャット履歴を表示
chat_history = get_chat_history()
for chat in chat_history:
    if chat["role"] == "USER":
        st.write(f"**User:** {chat['message']}")
    else:
        st.write(f"**Chatbot:** {chat['message']}")

# ユーザーからの入力を取得
user_input = st.text_input("User Input")

if st.button("Send"):
    # FastAPIエンドポイントにリクエストを送信
    headers = {"Authorization": f"Bearer {user_token}"}
    data = {"topic": topic, "message": user_input}
    response = requests.post("http://localhost:8000/chat", headers=headers, json=data)

    if response.status_code == 200:
        # チャット履歴を更新
        chat_history = get_chat_history()
    else:
        st.error("Error occurred while sending the request.")

if st.button("Reset Chat"):
    # FastAPIエンドポイントにリセットリクエストを送信
    headers = {"Authorization": f"Bearer {user_token}"}
    params = {"topic": topic}
    response = requests.post("http://localhost:8000/reset", headers=headers, params=params)

    if response.status_code == 200:
        # チャット履歴を更新
        chat_history = get_chat_history()
        st.success("Chat history has been reset for the current topic.")
    else:
        st.error("Error occurred while resetting the chat history.")