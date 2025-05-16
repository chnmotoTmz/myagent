import os
from dotenv import load_dotenv
from api_utils import generate_response_gemini, generate_response_cohere

load_dotenv()
API_TOKEN_1 = os.getenv("API_TOKEN_1")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

def main():
    conversation_history = []

    while True:
        user_message = input("あなた: ")
        if user_message.lower() == "exit":
            break

        conversation_history.append({"role": "USER", "message": user_message})

        # エージェント1 (Gemini)
        agent1_response = generate_response_gemini(
            "\n".join([f"{msg['role']}: {msg['message']}" for msg in conversation_history]), 
            API_TOKEN_1, 
            role="放送作家"
        )
        print(f"エージェント1: {agent1_response}")
        conversation_history.append({"role": "AGENT1", "message": agent1_response})

        # エージェント2 (Cohere)
        agent2_response = generate_response_cohere(
            conversation_history, 
            "",  # Cohereはチャット履歴全体を渡すので、messageは空にする
            role="プロデューサー"
        )
        print(f"エージェント2: {agent2_response}")
        conversation_history.append({"role": "AGENT2", "message": agent2_response})

if __name__ == "__main__":
    main()