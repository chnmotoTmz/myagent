import requests
import json
import os
import re
from collections import Counter
from api_utils import setup_logging, generate_response
def main():
    """チャットボットのメイン関数"""
    print("チャットボットと対話を始めます。終了するには 'exit' と入力してください。")

    # 初期設定
    chat_history = []
    num_turns = int(input("会話のターン数を入力してください: "))
    google_api_key = os.getenv("API_TOKEN_1")  # 環境変数からGoogle API Keyを取得
    cohere_api_key = os.getenv("COHERE_API_KEY")
    if not google_api_key or not cohere_api_key:
        print("エラー: 環境変数 GOOGLE_API_KEY と COHERE_API_KEY を設定してください。")
        return

    while True:
        # ユーザーからの最初の入力
        user_input = input("最初のメッセージを入力してください: ")
        if user_input.lower() == 'exit':
            print("チャットを終了します。")
            break

        chat_history.append({"role": "USER", "message": user_input})

        # 自動会話の回数を入力
        try:
            num_turns = int(input("ボット同士の会話回数を入力してください: "))
        except ValueError:
            print("無効な入力です。デフォルトの5回に設定します。")
            num_turns = 5

        # 自動会話ループ
        for turn in range(num_turns):
            response, chat_history = generate_response(chat_history, "", google_api_key, cohere_api_key)
            print(f"ボット{turn % 2 + 1}: {response}")

        print("\n自動会話が終了しました。次の指示を入力してください。")

        # ユーザーの介入を待つループ
        while True:
            user_input = input("あなた: ")
            if user_input.lower() == 'exit':
                print("チャットを終了します。")
                return

            chat_history.append({"role": "USER", "message": user_input})
            response, chat_history = generate_response(chat_history, user_input, google_api_key, cohere_api_key)
            print(f"チャットボット: {response}")

            # 次の自動会話に進むかどうかを確認
            continue_auto = input("自動会話を続けますか？ (y/n): ").lower()
            if continue_auto == 'y':
                break

if __name__ == "__main__":
    main()