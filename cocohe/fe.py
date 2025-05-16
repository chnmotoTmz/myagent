import gradio as gr
import requests
import json
from dotenv import load_dotenv
import os
import base64
from PIL import Image
import io

load_dotenv()
API_TOKEN_1 = os.getenv("API_TOKEN_1")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

# Image processing functions (from ocr.py)
def log_result(image_name, result):
    with open("process_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(f"Image: {image_name}, Result: {result}\n")

def generate_response_with_image(prompt, encoded_image, api_token, max_retries=3, initial_delay=1):
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
    params = {'key': api_token}

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
            response.raise_for_status()
            result = response.json()
            
            if 'candidates' in result and result['candidates']:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    return candidate['content']['parts'][0].get('text', "Error: No text in response")
                else:
                    return "Error: Unexpected response structure"
            else:
                return "Error: No candidates in response"
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                print(f"Error occurred. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                return f"Error: {str(e)}"
    return "Error: Max retries reached"

def encode_image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def process_images(images, prompt_text):
    results = []
    
    if not images:
        return "Error: No images provided"
    
    if not prompt_text:
        return "Error: No prompt text provided"
    
    for image in images:
        try:
            with Image.open(image.name) as img:
                encoded_image = encode_image_to_base64(img)
                response_text = generate_response_with_image(prompt_text, encoded_image, API_TOKEN_1)
                results.append(response_text)
                log_result(image.name, response_text)
        except Exception as e:
            error_message = f"Error processing image {image.name}: {str(e)}"
            results.append(error_message)
            log_result(image.name, error_message)
    
    return "\n\n".join(results)

# Chat functions (from fe.py)
def generate_chat_content(chat_history, message):
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

def chat(user_role, user_message, chatbot_role, chatbot_message, user_input, chat_history):
    chat_history = [
        {"role": user_role, "message": user_message},
        {"role": chatbot_role, "message": chatbot_message}
    ]
    chat_history.append({"role": "USER", "message": user_input})
    response_message = generate_chat_content(chat_history, user_input)
    chat_history.append({"role": "CHATBOT", "message": response_message})
    return chat_history, response_message

# Gradio interface
with gr.Blocks() as iface:
    gr.Markdown("# AI Image Analysis and Chat Application")
    
    with gr.Tabs():
        with gr.TabItem("Image Analysis"):
            images = gr.File(label="Upload Images", file_count="multiple")
            prompt_text = gr.Textbox(label="Image Analysis Prompt", placeholder="Describe what you want to know about the images")
            image_output = gr.Textbox(label="Image Analysis Results")
            image_submit = gr.Button("Analyze Images")
        
        with gr.TabItem("Chat Application"):
            user_role = gr.Textbox(label="User Role", value="USER")
            user_message = gr.Textbox(label="User Message", value="あなたはスターダストレビューの根本要です")
            chatbot_role = gr.Textbox(label="Chatbot Role", value="CHATBOT")
            chatbot_message = gr.Textbox(label="Chatbot Message", value="はい、私は確かにスターダストレビューの根本要です。作曲のスキルもあります")
            user_input = gr.Textbox(label="User Input")
            chat_output = gr.Textbox(label="Generated Content")
            chat_submit = gr.Button("Submit")
    
    chat_history = gr.State([])
    
    image_submit.click(
        process_images,
        inputs=[images, prompt_text],
        outputs=[image_output]
    )
    
    chat_submit.click(
        chat,
        inputs=[user_role, user_message, chatbot_role, chatbot_message, user_input, chat_history],
        outputs=[chat_history, chat_output]
    )



iface.launch(share=False)  # 公開リンクを作成するために share=True を追加
