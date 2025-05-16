import tkinter as tk
from tkinter import scrolledtext
import requests
import json
from dotenv import load_dotenv
import os
import threading
import time

load_dotenv()
API_TOKEN_1 = os.getenv("API_TOKEN_1")
API_TOKEN_2 = os.getenv("API_TOKEN_2")

conversation_history = []

def log_request(data, api_token):
    """Log the API request data to a file."""
    with open("api_requests.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"API Token: {api_token}\n")
        log_file.write(f"Request Data: {json.dumps(data, ensure_ascii=False, indent=2)}\n")
        log_file.write("\n")

def generate_response(prompt, api_token):
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    params = {'key': api_token}

    log_request(data, api_token)

    try:
        response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and result['candidates']:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Error: Unable to generate response"
    except requests.RequestException as e:
        return f"Error: {str(e)}"

def continue_conversation():
    global conversation_history

    repeat_count = int(repeat_entry.get())

    for _ in range(repeat_count):
        for agent_num, api_token, agent_prompt in [(1, API_TOKEN_1, agent_1_prompt_entry.get("1.0", tk.END).strip()), (2, API_TOKEN_2, agent_2_prompt_entry.get("1.0", tk.END).strip())]:
            update_chat_history(f"エージェント{agent_num}が考え中...\n")
            full_prompt = agent_prompt
            
            truncated_history = conversation_history[-5:]
            for message in truncated_history:
                full_prompt += f"{message['speaker']}: {message['content']}\n"

            agent_response = generate_response(full_prompt, api_token)
            conversation_history.append({"speaker": f"agent_{agent_num}", "content": agent_response})
            update_chat_history(f"エージェント{agent_num}: {agent_response}\n")
            
            time.sleep(2)

    update_chat_history("会話は終了しました。\n\n")
    input_field.config(state="normal")
    send_button.config(state="normal")

def send_message():
    user_message = input_field.get()
    input_field.delete(0, tk.END)
    input_field.config(state="disabled")
    send_button.config(state="disabled")

    conversation_history.append({"speaker": "user", "content": user_message})
    update_chat_history(f"あなた: {user_message}\n")

    threading.Thread(target=continue_conversation, daemon=True).start()

def update_chat_history(message):
    chat_history.config(state="normal")
    chat_history.insert(tk.END, message)
    chat_history.see(tk.END)
    chat_history.config(state="disabled")

def maximize_window():
    window.state('zoomed')

def clear_chat_history():
    global conversation_history
    conversation_history = []
    chat_history.config(state="normal")
    chat_history.delete(1.0, tk.END)
    chat_history.config(state="disabled")

window = tk.Tk()
window.title("チャットアプリ")

chat_history = scrolledtext.ScrolledText(window, state="disabled", height=20, width=50)
chat_history.pack(padx=10, pady=10)

input_field = tk.Entry(window, width=50)
input_field.pack(padx=10, pady=(0, 10))

send_button = tk.Button(window, text="送信", command=send_message)
send_button.pack(pady=(0, 10))

repeat_label = tk.Label(window, text="リピート回数:")
repeat_label.pack()
repeat_entry = tk.Entry(window, width=5)
repeat_entry.insert(0, "10")
repeat_entry.pack()

agent_1_prompt_label = tk.Label(window, text="エージェント1のプロンプト:")
agent_1_prompt_label.pack()
agent_1_prompt_entry = tk.Text(window, height=5, width=50)
agent_1_prompt_entry.insert(tk.END, "あなたは放送作家です。\n{knowledge_source_1}")
agent_1_prompt_entry.pack()

agent_2_prompt_label = tk.Label(window, text="エージェント2のプロンプト:")
agent_2_prompt_label.pack()
agent_2_prompt_entry = tk.Text(window, height=5, width=50)
agent_2_prompt_entry.insert(tk.END, "あなたはプロデューサーです。\n{knowledge_source_2}")
agent_2_prompt_entry.pack()

clear_button = tk.Button(window, text="チャット履歴をクリア", command=clear_chat_history)
clear_button.pack(pady=(10, 0))

maximize_button = tk.Button(window, text="最大化", command=maximize_window)
maximize_button.pack(pady=(10, 10))

window.mainloop()