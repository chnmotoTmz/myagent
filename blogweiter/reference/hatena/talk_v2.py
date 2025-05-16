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
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

conversation_history = []

def log_request(data, api_token):
    """Log the API request data to a file."""
    with open("api_requests.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"API Token: {api_token}\n")
        log_file.write(f"Request Data: {json.dumps(data, ensure_ascii=False, indent=2)}\n")
        log_file.write("\n")

def generate_response_gemini(prompt, api_token):
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

def generate_response_cohere(chat_history, message):
    url = "https://api.cohere.ai/v1/chat"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": COHERE_API_KEY
    }
    data = {
        "chat_history": chat_history,
        "message": message,
        "connectors": [{"id": "web-search"}]
    }
    
    log_request(data, "Cohere API")

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        result = response.json()
        if 'text' in result:
            return result['text']
        else:
            return "Error: No 'text' key found in the API response"
    except requests.RequestException as e:
        return f"Error: {str(e)}"

def continue_conversation2():
    global conversation_history

    repeat_count = int(repeat_entry.get())

    for _ in range(repeat_count):
        for agent_num, api_type, agent_prompt in [
            (1, "gemini", agent_1_prompt_entry.get("1.0", tk.END).strip()),
            (2, "cohere", agent_2_prompt_entry.get("1.0", tk.END).strip())
        ]:
            update_chat_history(f"エージェント{agent_num}が考え中...\n")
            
            if api_type == "gemini":
                full_prompt = agent_prompt
                truncated_history = conversation_history[-5:]
                for message in truncated_history:
                    full_prompt += f"{message['speaker']}: {message['content']}\n"
                agent_response = generate_response_gemini(full_prompt, API_TOKEN_1)
            else:  # cohere
                cohere_chat_history = [
                    {"role": "USER", "message": user_message_entry.get("1.0", tk.END).strip()},
                    {"role": "CHATBOT", "message": chatbot_message_entry.get("1.0", tk.END).strip()}
                ]
                cohere_chat_history.extend([
                    {"role": "USER" if msg['speaker'] == "user" else "CHATBOT", "message": msg['content']}
                    for msg in conversation_history[-3:]  # Only include the last 3 messages
                ])
                agent_response = generate_response_cohere(cohere_chat_history, agent_prompt)

            conversation_history.append({"speaker": f"agent_{agent_num}", "content": agent_response})
            update_chat_history(f"エージェント{agent_num}: {agent_response}\n")
            
            time.sleep(2)

def continue_conversation():
    global conversation_history

    repeat_count = int(repeat_entry.get())

    agent_1_memory = []
    agent_2_memory = []

    for _ in range(repeat_count):
        for agent_num, api_type, agent_prompt, agent_memory in [
            (1, "gemini", agent_1_prompt_entry.get("1.0", tk.END).strip(), agent_1_memory),
            (2, "cohere", agent_2_prompt_entry.get("1.0", tk.END).strip(), agent_2_memory)
        ]:
            update_chat_history(f"エージェント{agent_num}が考え中...\n")
            
            if api_type == "gemini":
                full_prompt = agent_prompt  # Start with the agent's role/persona
                
                # Add agent's memory of the conversation
                for message in agent_memory:
                    full_prompt += f"{message['speaker']}: {message['content']}\n"

                # Add recent conversation history (limited to avoid exceeding token limits)
                truncated_history = conversation_history[-5:]
                for message in truncated_history:
                    full_prompt += f"{message['speaker']}: {message['content']}\n"

                agent_response = generate_response_gemini(full_prompt, API_TOKEN_1)
            else:  # cohere
                cohere_chat_history = [
                    {"role": "USER", "message": user_message_entry.get("1.0", tk.END).strip()},
                    {"role": "CHATBOT", "message": chatbot_message_entry.get("1.0", tk.END).strip()}
                ]
                
                # Add agent's memory to Cohere's chat history
                cohere_chat_history.extend([
                    {"role": "USER" if msg['speaker'] == "user" else "CHATBOT", "message": msg['content']}
                    for msg in agent_memory[-3:]  # Limit memory for Cohere as well
                ])
                
                # Add recent history
                cohere_chat_history.extend([
                    {"role": "USER" if msg['speaker'] == "user" else "CHATBOT", "message": msg['content']}
                    for msg in conversation_history[-3:] 
                ])
                
                agent_response = generate_response_cohere(cohere_chat_history, agent_prompt)

            conversation_history.append({"speaker": f"agent_{agent_num}", "content": agent_response})
            agent_memory.append({"speaker": f"agent_{agent_num}", "content": agent_response}) # Add to agent's memory
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

user_role_label = tk.Label(window, text="User Role:")
user_role_label.pack()
user_role_entry = tk.Entry(window, width=50)
user_role_entry.insert(0, "USER")
user_role_entry.pack()

user_message_label = tk.Label(window, text="User Message:")
user_message_label.pack()
user_message_entry = tk.Text(window, height=2, width=50)
user_message_entry.insert(tk.END, "あなたは（ここにロール）です")
user_message_entry.pack()

chatbot_role_label = tk.Label(window, text="Chatbot Role:")
chatbot_role_label.pack()
chatbot_role_entry = tk.Entry(window, width=50)
chatbot_role_entry.insert(0, "CHATBOT")
chatbot_role_entry.pack()

chatbot_message_label = tk.Label(window, text="Chatbot Message:")
chatbot_message_label.pack()
chatbot_message_entry = tk.Text(window, height=2, width=50)
chatbot_message_entry.insert(tk.END, "はい、私は確かに（ここにロール）です")
chatbot_message_entry.pack()

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