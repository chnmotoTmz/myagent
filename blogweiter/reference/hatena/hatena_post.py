import os
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib
import random
import base64
from dotenv import load_dotenv
load_dotenv()

def load_credentials(username):
    """はてなAPIアクセスに必要な認証情報をタプルの形式で返す"""
    auth_token = os.getenv("HATENA_BLOG_ATOMPUB_KEY_1")
    message = "環境変数`HATENA_BLOG_ATOMPUB_KEY`にAtomPubのAPIキーを設定してください"
    assert auth_token, message
    return (username, auth_token)

def wsse(username, api_key):
    created = datetime.now().isoformat() + "Z"
    b_nonce = hashlib.sha1(str(random.random()).encode()).digest()
    b_digest = hashlib.sha1(b_nonce + created.encode() + api_key.encode()).digest()
    c = 'UsernameToken Username="{0}", PasswordDigest="{1}", Nonce="{2}", Created="{3}"'
    return c.format(username, base64.b64encode(b_digest).decode(), base64.b64encode(b_nonce).decode(), created)

def create_post_data(title, body, username, draft='no'):
    now = datetime.now()
    dtime = now.strftime("%Y-%m-%dT%H:%M:%S")
    template = '''<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">
    <title>{0}</title>
    <author><name>{1}</name></author>
    <content type="text/html">{2}</content>
    <updated>{3}</updated>
    <category term="" />
    <app:control>
        <app:draft>{4}</app:draft>
    </app:control>
</entry>'''
    data = template.format(
        title,
        username,
        body.strip(),  # 余分な空白を除去
        dtime,
        draft
    ).encode('utf-8')
    return data


def post_to_hatena(username, blog_domain, api_key, title, body, draft='no'):
    data = create_post_data(title, body, username, draft)
    headers = {'X-WSSE': wsse(username, api_key)}
    url = f'http://blog.hatena.ne.jp/{username}/{blog_domain}/atom/entry'
    r = requests.post(url, data=data, headers=headers)
    return r.status_code, r.text

def retrieve_hatena_blog_entries(blog_entries_uri, user_pass_tuple):
    """はてなブログAPIにGETアクセスし、記事一覧を表すXMLを文字列で返す"""
    r = requests.get(blog_entries_uri, auth=user_pass_tuple)
    return r.text

def select_elements_of_tag(xml_root, tag):
    """返り値のXMLを解析し、指定したタグを持つ子要素をすべて返す"""
    return xml_root.findall(tag)

def return_next_entry_list_uri(links):
    """続くブログ記事一覧のエンドポイントを返す"""
    for link in links:
        if link.attrib["rel"] == "next":
            return link.attrib["href"]

def is_draft(entry):
    """ブログ記事がドラフトかどうか判定する"""
    draft_status = (
        entry.find("{http://www.w3.org/2007/app}control")
        .find("{http://www.w3.org/2007/app}draft")
        .text
    )
    return draft_status == "yes"

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

def get_public_link(entry):
    links = entry.findall("{http://www.w3.org/2005/Atom}link")
    for link in links:
        if link.get("rel") == "alternate" and link.get("type") == "text/html":
            return link.get("href")
    return None

if __name__ == "__main__":

    hatena_id = "motochan1969"
    blog_domain = "lifehacking1919.hatenablog.jp"

    # 認証情報の取得
    user_pass_tuple = load_credentials(hatena_id)
    username, api_key = user_pass_tuple

    # 投稿機能のデモ
    title = "テスト投稿"
    body = "<p>これはテスト投稿です。</p>"
    status_code, response_text = post_to_hatena(username, blog_domain, api_key, title, body)
    print(f"投稿ステータス: {status_code}")
    print(f"レスポンス: {response_text}")

    # 記事一覧の取得
    root_endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_domain}/atom"
    blog_entries_uri = f"{root_endpoint}/entry"

    target_entries = []

    while blog_entries_uri:
        entries_xml = retrieve_hatena_blog_entries(blog_entries_uri, user_pass_tuple)
        root = ET.fromstring(entries_xml)

        links = select_elements_of_tag(root, "{http://www.w3.org/2005/Atom}link")
        blog_entries_uri = return_next_entry_list_uri(links)

        entries = select_elements_of_tag(root, "{http://www.w3.org/2005/Atom}entry")
        for entry in entries:
            if is_draft(entry):
                continue
            target_entries.append(entry)

    # 記事情報の保存
    with open("hatena_blog_entries2.csv", "w", encoding="utf-8") as file:
        for entry in target_entries:
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            link = get_public_link(entry)
            if link is None:
                continue
            content_element = entry.find("{http://www.w3.org/2005/Atom}content")
            content_html = ET.tostring(content_element, encoding='unicode', method='xml')
            content_html = content_html.replace('<content xmlns="http://www.w3.org/2005/Atom" type="text/html">', '').replace('</content>', '')
            japanese_text = extract_japanese_text(content_html)
            file.write(f"Title: {title},Link: {link}: {japanese_text}\n")

    print("記事の情報がファイル 'hatena_blog_entries.csv' に保存されました。")