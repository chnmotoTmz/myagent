import os
import requests
from bs4 import BeautifulSoup

def load_qiita_token():
    """Qiitaのアクセストークンをロードする"""
    token = os.getenv("QIITA_ACCESS_TOKEN")
    message = "環境変数`QIITA_ACCESS_TOKEN`にQiitaのアクセストークンを設定してください"
    assert token, message
    return token

def retrieve_qiita_articles(token, page=1, per_page=100):
    """QiitaのAPIを使用して記事を取得する"""
    url = f"https://qiita.com/api/v2/authenticated_user/items?page={page}&per_page={per_page}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def extract_japanese_text(html_content):
    """HTMLコンテンツから日本語テキストを抽出する"""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text()
    japanese_text = ''.join(char for char in text if is_japanese(char))
    return japanese_text

def is_japanese(char):
    """文字が日本語かどうかを判定する"""
    return any([
        '\u3040' <= char <= '\u30ff',  # Hiragana and Katakana
        '\u4e00' <= char <= '\u9faf',  # CJK Unified Ideographs
        '\u3000' <= char <= '\u303f',  # Punctuation
    ])

def extract_text(entry):
    japanese_text = extract_japanese_text(entry)
    return japanese_text

if __name__ == "__main__":
    token = load_qiita_token()
    all_articles = []
    page = 1

    while True:
        articles = retrieve_qiita_articles(token, page)
        if not articles:
            break
        all_articles.extend(articles)
        page += 1

    with open("qiita_articles.csv", "w", encoding="utf-8") as file:
        for article in all_articles:
            title = article['title']
            link = article['url']
            content = extract_text(article['rendered_body'])
            file.write(f"Title: {title}, Link: {link}: {content}\n")

    print("記事の情報がファイル 'qiita_articles.csv' に保存されました。")
