import gradio as gr
import requests
import json

import xml.etree.ElementTree as ET
from hatena import load_credentials, retrieve_hatena_blog_entries, select_elements_of_tag, return_next_entry_list_uri, is_draft, get_public_link
from rakuten_ import generate_rakuten_affiliate_link
from hatena_post import post_to_hatena
import os
import pdb
from rakuten_ import generate_rakuten_affiliate_link
from dotenv import load_dotenv
import os
import requests
import json
import csv
import re
import html

google_api_key = os.getenv("API_TOKEN_1")  # 環境変数からGoogle API Keyを取得
cohere_api_key = os.getenv("COHERE_API_KEY")


load_dotenv()

def get_blog_entries():
    # はてなブログの設定
    hatena_id = "motochan1969"
    blog_domain = "lifehacking1919.hatenablog.jp"

    # 認証情報の取得
    user_pass_tuple = load_credentials(hatena_id)

    # root endpointを設定
    root_endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_domain}/atom"
    blog_entries_uri = f"{root_endpoint}/entry"

    entries = []

    while blog_entries_uri:
        print(f"Requesting entries from: {blog_entries_uri}")  # デバッグ用
        entries_xml = retrieve_hatena_blog_entries(blog_entries_uri, user_pass_tuple)
        root = ET.fromstring(entries_xml)

        links = select_elements_of_tag(root, "{http://www.w3.org/2005/Atom}link")
        blog_entries_uri = return_next_entry_list_uri(links)

        entry_elements = select_elements_of_tag(root, "{http://www.w3.org/2005/Atom}entry")
        for entry in entry_elements:
            if is_draft(entry):
                continue
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            entry_id = entry.find("{http://www.w3.org/2005/Atom}id").text
            api_link = entry.find("{http://www.w3.org/2005/Atom}link[@rel='edit']").get('href')
            if api_link:
                print(f"Found entry: {title} - {api_link}")  # デバッグ用
                entries.append(f"{title}|{api_link}")

    return entries



def cohere_api_request(payload):
    url = "https://api.cohere.ai/v1/chat"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": os.getenv("COHERE_API_KEY")
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"APIリクエストエラー: {e}")
    except json.JSONDecodeError as e:
        print(f"JSONデコードエラー: {e}")
    except Exception as e:
        print(f"予期せぬエラー: {e}")
    return None

def extract_keywords(content):
    chat_history = [
        {"role": "USER", "message": "あなたは専門的なブログ解析AIです。与えられた記事から重要なキーワードを抽出する任務があります。"},
        {"role": "CHATBOT", "message": "はい、承知しました。記事の内容を詳細に分析し、最も重要で代表的なキーワードを抽出いたします。"},
        {"role": "USER", "message": "キーワードは以下の条件を満たす必要があります：\n1. 記事の主題を適切に表現している\n2. 一般的で検索されやすい単語や短いフレーズである\n3. 製品名や固有名詞がある場合は、それらを優先的に含める\n4. 長すぎる単語や複雑な表現は避ける\n5. カタカナ語と日本語の両方を考慮する"},
        {"role": "CHATBOT", "message": "了解しました。これらの条件に基づいて、最適なキーワードを選択いたします。特に製品名や固有名詞を優先的に抽出します。"},
    ]

    payload = {
        "chat_history": chat_history,
        "message": f"""以下の記事から条件に合致するキーワードを正確に10個抽出してください。特に製品名や商品名を優先的に抽出してください。頻出語句は避けてください
        出力形式: キーワード1, キーワード2, キーワード3, キーワード4, キーワード5, キーワード6, キーワード7, キーワード8, キーワード9, キーワード10
        注意事項:
        - キーワードは必ず10個にしてください。
        - カンマと半角スペースで区切ってください。
        - キーワードの前後に余分な空白を入れないでください。
        - 出力は上記の形式のみとし、説明や追加のコメントは不要です。
        - 製品名や商品名を優先的に抽出し、それらが含まれていることを確認してください。

        記事本文:
        {content}
        """,
        "connectors": [],
        "prompt_truncation": "AUTO"
    }

    result = cohere_api_request(payload)
    if result and 'text' in result:
        keywords = result['text'].strip().split(', ')
        if len(keywords) == 10:
            return keywords
        else:
            print(f"警告: 抽出されたキーワードの数が10個ではありません。実際の数: {len(keywords)}")
            return keywords[:10] if len(keywords) > 10 else keywords + [''] * (10 - len(keywords))
    return []

def generate_affiliate_links(keywords):
    affiliate_links = []
    for keyword in keywords:
        if keyword:  # 空の文字列でないことを確認
            link = generate_rakuten_affiliate_link(keyword)
            if link:
                affiliate_links.append((keyword, link))
    return affiliate_links



def preview_content(content):
    # HTMLエスケープ
    escaped_content = html.escape(content)
    
    # 改行を<br>タグに変換
    formatted_content = escaped_content.replace('\n', '<br>')
    
    # プレビュー用のHTMLテンプレート
    preview_html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>記事プレビュー</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            a {{
                color: #0066cc;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
    </head>
    <body>
        <div class="article-content">
            {formatted_content}
        </div>
    </body>
    </html>
    """
    
    return preview_html


from hatena_post import post_to_hatena
import os

def post_updated_content(title, content):
    # はてなブログの設定
    hatena_id = "motochan1969"
    blog_domain = "arafo40tozan.hatenadiary.jp"
    
    # APIキーを環境変数から取得
    api_key = os.getenv("HATENA_BLOG_ATOMPUB_KEY_1")
    
    if not api_key:
        return "エラー: HATENA_BLOG_ATOMPUB_KEY が設定されていません。"

    try:
        # 記事を投稿
        status_code, response_text = post_to_hatena(hatena_id, blog_domain, api_key, title, content)
        
        # ステータスコードに基づいてメッセージを返す
        if status_code == 201:
            return f"成功: 記事「{title}」が正常に投稿されました。"
        elif status_code == 200:
            return f"成功: 記事「{title}」が正常に更新されました。"
        else:
            return f"エラー: 投稿に失敗しました。ステータスコード: {status_code}, レスポンス: {response_text}"
    
    except Exception as e:
        return f"エラー: 投稿処理中に例外が発生しました。{str(e)}"
    

def process_and_post(selected_article, updated_content):
    title = selected_article.split(',')[0]  # タイトルを取得（カンマで分割された最初の要素）
    result = post_updated_content(title, updated_content)
    return result

def get_article_content(selected_article):
    title, api_url = selected_article.split('|', 1)
    hatena_id = "motochan1969"
    user_pass_tuple = load_credentials(hatena_id)

    print(f"Requesting: {api_url}")  # デバッグ用

    response = requests.get(api_url, auth=user_pass_tuple)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        content_element = root.find('{http://www.w3.org/2005/Atom}content')
        
        if content_element is not None:
            content_type = content_element.get('type', '')
            if content_type == 'html':
                return content_element.text
            else:
                # HTMLでない場合は、テキストを適切にHTMLに変換
                return f"<p>{html.escape(content_element.text).replace('\n', '<br>')}</p>"
        else:
            return "<p>エラー: 記事のコンテンツが見つかりません。</p>"
    else:
        return f"<p>エラー: 記事の取得に失敗しました。ステータスコード: {response.status_code}</p>"
    
    
import re
from html import escape

import re
from bs4 import BeautifulSoup, NavigableString


import re

def replace_keywords_with_links(html_content, replacements):
    for keyword, link_html in replacements:
        # href属性を抽出
        href_match = re.search(r'href="([^"]*)"', link_html)
        if href_match:
            href = href_match.group(1)
            
            # target属性を抽出（存在する場合）
            target_match = re.search(r'target="([^"]*)"', link_html)
            target_attr = f' target="{target_match.group(1)}"' if target_match else ''
            
            # 新しいリンクを作成
            new_link = f'<a href="{href}"{target_attr}>{keyword}</a>'
            
            # キーワードを新しいリンクで置換
            pattern = re.compile(re.escape(keyword))
            html_content = pattern.sub(new_link, html_content)
    
    return html_content


def process_article(selected_article):
    content_html = get_article_content(selected_article)
    if content_html.startswith("<p>エラー:"):
        return content_html, "", "", "", "", ""
    
    print("Original Content:", content_html[:500])
    soup = BeautifulSoup(content_html, 'html.parser')
    content_text = soup.get_text()
    
    keywords = extract_keywords(content_text)
    print("Extracted Keywords:", keywords)
    
    affiliate_links = generate_affiliate_links(keywords)
    print("Generated Affiliate Links:", affiliate_links)
    
    updated_content = replace_keywords_with_links(content_html, affiliate_links)
    print("Updated Content:", updated_content[:500])
    
    preview_html = preview_content(updated_content)
    return content_html, keywords, affiliate_links, updated_content, preview_html, updated_content

# ... (他の関数: get_blog_entries, extract_keywords, generate_affiliate_links, preview_content, post_updated_content, process_and_post, get_article_content, replace_keywords_with_links, process_article) ...
from api_utils import generate_response_google, summarize_chat_history_google

def generate_article(content, existing_content, google_api_key):
   
    """コンテンツと既存記事の内容から新しい記事を生成する"""

    # Google APIを使って、コンテンツから必要な項目を生成
    chat_history = [
        {"role": "USER", "message": "あなたは専門的なブログ記事生成AIです。与えられたコンテンツから、ブログ記事に必要な項目を生成する任務があります。"},
        {"role": "CHATBOT", "message": "はい、承知しました。コンテンツを分析し、必要な項目を生成いたします。"},
    ]

    # プロンプトの作成
    prompt = f"""ブログ記事を2000字で書きたい、タイトルと、画像生成ＡＩ用Imagecreator用のプロンプトも書いて（最後に、minitureをつけること）実際にブログ記事を作成する際には、独自の情報や視点を加えて、オリジナルの記事を作成してください。著作権や肖像権などに配慮し、適切な情報を使用してください。
    #出力形式:
    カテゴリ: {{カテゴリ}}
    タイトル例: {{タイトル例}}
    プロンプト: {{プロンプト}}
    参考記事: {{参考記事}}
    Imagecreatorプロンプト: {{Imagecreatorプロンプト}}, miniature 
    商品アフェリエイト: {{商品アフェリエイト}}
    コンテンツ: {re.escape(content)}
    """

    generated_text, _ = generate_response_google(chat_history, prompt, google_api_key)

    if generated_text.startswith("Error:"):
        return None, None  # エラーが発生した場合は None を返す

    # 生成されたテキストから各項目を抽出
    try:
        category = re.search(r"カテゴリ: (.+)", generated_text).group(1)
        title_example = re.search(r"タイトル例: (.+)", generated_text).group(1)
        prompt = re.search(r"プロンプト: (.+)", generated_text).group(1)
        reference_article = re.search(r"参考記事: (.+)", generated_text).group(1)
        image_creator_prompt = re.search(r"Imagecreatorプロンプト: (.+), miniature", generated_text).group(1)
        affiliate_products = re.search(r"商品アフェリエイト: (.+)", generated_text).group(1)
        generated_article= re.search(r"コンテンツ: (.+)", generated_text).group(1)
    except AttributeError:
        # 正規表現で項目が見つからなかった場合
        return None, None

    # 既存記事の口調を分析 (Cohere API を使用)
    # ... (口調分析の処理を実装) ...

    # 新しい記事本文を生成 (Google API を使用)
    # ... (記事生成の処理を実装。プロンプト、参考記事、アフェリエイト商品、締めくくりなどを利用) ...

    # 生成された記事本文に関連リンクを追加
    # ... (reference_article を適切な場所にリンクとして挿入) ...

    # 2000字程度になるように調整
    # ... (記事の長さを調整する処理を実装) ...

    return {
        "category": category,
        "title_example": title_example,
        "prompt": prompt,
        "reference_article": reference_article,
        "image_creator_prompt": image_creator_prompt,
        "affiliate_products": affiliate_products,
        "content": generated_article  # 生成された記事本文を格納
    }, image_creator_prompt


def process_csv(csv_file_path):
    results = []
    

    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # ヘッダー行をスキップ
        for row in reader:
            if len(row) >= 1:  # コンテンツがあることを確認
                content = row[0]

                # 既存記事は選択しないので空文字列を渡す
                generated_article, image_creator_prompt = generate_article(content, "", google_api_key)

                if generated_article is None:
                    # 記事生成に失敗した場合はスキップ
                    continue

                # キーワード抽出、アフィリエイトリンク生成、記事内容更新は process_article をそのまま利用

                
                content_html, keywords, affiliate_links, updated_content, preview_html, updated_content_preview = process_article(f"{generated_article['title_example']}|{''}")  # API URLは不要になったので空文字列にする

                updated_content = generated_article['content']  # 生成された記事内容で上書き

                # 投稿結果をリストに追加
                post_result = post_updated_content(generated_article['title_example'], updated_content)
                results.append({
                    "title": generated_article['title_example'],
                    "api_url": generated_article['reference_article'],
                    "keywords": keywords,
                    "affiliate_links": affiliate_links,
                    "updated_content": updated_content,
                    "image_creator_prompt": image_creator_prompt,
                    "post_result": post_result
                })
    return results


with gr.Blocks() as demo:
    gr.Markdown("# はてなブログアフィリエイト追加ツール")
  
    with gr.Row():
        article_list = gr.Dropdown(label="記事一覧", choices=get_blog_entries())
        process_btn = gr.Button("処理開始")
    
    with gr.Row():
        original_content = gr.Textbox(label="元の記事内容")
        preview = gr.HTML(label="プレビュー")
    
    with gr.Row():
        keywords = gr.Textbox(label="抽出されたキーワード")
        affiliate_links = gr.Textbox(label="生成されたアフィリエイトリンク")
   
    with gr.Row():
        updated_content_html = gr.Code(label="更新された記事内容 (HTML)", language="html")
        updated_content_preview = gr.HTML(label="更新された記事内容 (プレビュー)")
    
    post_btn = gr.Button("投稿")
    result = gr.Textbox(label="結果")
    
    process_btn.click(
        process_article, 
        inputs=[article_list], 
        outputs=[original_content, keywords, affiliate_links, updated_content_html, preview, updated_content_preview]
    )

    post_btn.click(post_updated_content, inputs=[article_list, updated_content_html], outputs=[result])
    post_btn.click(process_and_post, inputs=[article_list, updated_content_html], outputs=[result])

    csv_file_input = gr.File(label="CSVファイルを選択")
    process_csv_btn = gr.Button("CSV処理開始")

    results_output = gr.Dataframe(label="処理結果", headers=["title", "api_url", "keywords", "affiliate_links", "updated_content", "post_result"])

    process_csv_btn.click(process_csv, inputs=[csv_file_input], outputs=[results_output])

demo.launch()
