import os
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

def load_credentials(username):
    """はてなAPIアクセスに必要な認証情報をタプルの形式で返す"""
    auth_token = os.getenv("HATENA_BLOG_ATOMPUB_KEY_1")
    message = "環境変数`HATENA_BLOG_ATOMPUB_KEY`にAtomPubのAPIキーを設定してください"
    assert auth_token, message
    return (username, auth_token)

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
    # 固定されたユーザーIDとブログドメイン
    hatena_id = "motochan1969"
    #blog_domain = "lifehacking1919.hatenablog.jp"
    blog_domain = "arafo40tozan.hatenadiary.jp"

    user_pass_tuple = load_credentials(hatena_id)

    # root endpointを設定
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

            # メインの処理部分
    with open("hatena_blog_entries.csv", "w", encoding="utf-8") as file:
        for entry in target_entries:
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            link = get_public_link(entry)
            if link is None:
                continue  # リンクが見つからない場合はスキップ
            content_element = entry.find("{http://www.w3.org/2005/Atom}content")
            content_html = ET.tostring(content_element, encoding='unicode', method='xml')
            content_html = content_html.replace('<content xmlns="http://www.w3.org/2005/Atom" type="text/html">', '').replace('</content>', '')
            japanese_text = extract_japanese_text(content_html)
            file.write(f"Title: {title},Link: {link}: {japanese_text}\n")

    print("記事の情報がファイル 'hatena_blog_entries.csv' に保存されました。")
