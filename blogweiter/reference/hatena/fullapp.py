import os
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import json
import logging

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_env_var(env_var, error_message):
    """Load a variable from environment variables"""
    value = os.getenv(env_var)
    assert value, error_message
    return value

def retrieve_entries(url, auth=None, headers=None):
    """Generic function to retrieve entries from an API"""
    response = requests.get(url, auth=auth, headers=headers)
    response.raise_for_status()
    return response.text if auth else response.json()

def extract_japanese_text(html_content):
    """Extract Japanese text from HTML content"""
    soup = BeautifulSoup(html_content, "html.parser")
    return ''.join(char for char in soup.get_text() if is_japanese(char))

def is_japanese(char):
    """Check if a character is Japanese"""
    return any([
        '\u3040' <= char <= '\u30ff',  # Hiragana and Katakana
        '\u4e00' <= char <= '\u9faf',  # CJK Unified Ideographs
        '\u3000' <= char <= '\u303f',  # Punctuation
    ])

def load_last_processed_entries():
    """Load the last processed entries from a JSON file"""
    if os.path.exists('last_processed_entries.json'):
        with open('last_processed_entries.json', 'r') as f:
            return json.load(f)
    return {"hatena": {}, "qiita": None}

def save_last_processed_entries(last_processed):
    """Save the last processed entries to a JSON file"""
    with open('last_processed_entries.json', 'w') as f:
        json.dump(last_processed, f)

import re

def process_hatena_blogs(hatena_id, blog_domains, user_pass_tuple, output_file):
    logging.info("Starting to process Hatena blogs")
    for blog_domain in blog_domains:
        logging.info(f"Processing blog domain: {blog_domain}")
        blog_domain = blog_domain.strip()
        root_endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_domain}/atom"
        blog_entries_uri = f"{root_endpoint}/entry"
        target_entries = []
        while blog_entries_uri:
            logging.info(f"Retrieving entries for {blog_domain}")
            entries_xml = retrieve_entries(blog_entries_uri, auth=user_pass_tuple)
            root = ET.fromstring(entries_xml)
            links = root.findall("{http://www.w3.org/2005/Atom}link")
            blog_entries_uri = next((link.attrib["href"] for link in links if link.attrib["rel"] == "next"), None)
            entries = root.findall("{http://www.w3.org/2005/Atom}entry")
            for entry in entries:
                if entry.find("{http://www.w3.org/2007/app}control").find("{http://www.w3.org/2007/app}draft").text == "yes":
                    continue
                target_entries.append(entry)
        logging.info(f"Finished processing {len(target_entries)} entries for {blog_domain}")
        with open(output_file, "a", encoding="utf-8") as file:
            for entry in reversed(target_entries):
                title = entry.find("{http://www.w3.org/2005/Atom}title").text
                link = next((link.get("href") for link in entry.findall("{http://www.w3.org/2005/Atom}link") 
                             if link.get("rel") == "alternate" and link.get("type") == "text/html"), None)
                if link is None:
                    continue
                content_element = entry.find("{http://www.w3.org/2005/Atom}content")
                content_html = ET.tostring(content_element, encoding='unicode', method='xml')
                content_html = content_html.replace('<content xmlns="http://www.w3.org/2005/Atom" type="text/html">', '').replace('</content>', '')
                japanese_text = extract_japanese_text(content_html)
                japanese_text = japanese_text.strip()  # 前後の空白を削除
                
                # 本文が実質的な内容を持つかチェック
                if is_valid_content(japanese_text):
                    file.write(f"Hatena Blog: {blog_domain}, Title: {title}, Link: {link}: {japanese_text}\n")

def is_valid_content(text):
    # 空白文字、記号のみ、または極端に短い文章を除外
    text = re.sub(r'\s+', '', text)  # 全ての空白文字を削除
    text = re.sub(r'[、。,.!?！？]+', '', text)  # 句読点を削除
    if len(text) <= 20:
        return False
    
    # 単語の繰り返しやリストのような内容を除外
    words = text.split()
    if len(set(words)) < len(words) * 0.5:  # 単語の半分以上が重複している場合
        return False
    
    return True

def process_qiita_articles(qiita_token, last_processed_entries, output_file):
    logging.info("Starting to process Qiita articles")

    """Process Qiita articles"""
    all_articles = []
    page = 1
    last_processed_qiita_id = last_processed_entries.get("qiita")

    while True:
        logging.info(f"Retrieving Qiita articles page {page}")

        articles = retrieve_entries(f"https://qiita.com/api/v2/authenticated_user/items?page={page}&per_page=100", 
                                    headers={"Authorization": f"Bearer {qiita_token}"})
        if not articles:
            break
        for article in articles:
            if article['id'] == last_processed_qiita_id:
                break
            all_articles.append(article)
        if last_processed_qiita_id and len(all_articles) >= 10:
            break
        page += 1
    
    logging.info(f"Finished processing {len(all_articles[:10])} new Qiita articles")

    with open(output_file, "a", encoding="utf-8") as file:
        for article in all_articles:
            title = article['title']
            link = article['url']
            content = extract_japanese_text(article['rendered_body'])
            file.write(f"Qiita: Title: {title}, Link: {link}: {content}\n")

    if all_articles:
        last_processed_entries["qiita"] = all_articles[0]['id']


def remove_duplicates(text):
    """Remove duplicate lines from the text"""
    lines = text.split('\n')
    unique_lines = []
    seen = set()
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    return '\n'.join(unique_lines)




if __name__ == "__main__":
    hatena_id = load_env_var("HATENA_ID", "Set Hatena ID in the environment variable `HATENA_ID`.")
    blog_domains = load_env_var("BLOG_DOMAINS", "Set blog domains in the environment variable `BLOG_DOMAINS`.").split(",")
    hatena_api_key = load_env_var("HATENA_BLOG_ATOMPUB_KEY", "Set AtomPub API key in the environment variable `HATENA_BLOG_ATOMPUB_KEY`.")
    user_pass_tuple = (hatena_id, hatena_api_key)
    qiita_token = load_env_var("QIITA_ACCESS_TOKEN", "Set Qiita access token in the environment variable `QIITA_ACCESS_TOKEN`.")

    output_file = "blog_and_qiita_entries.csv"
    last_processed_entries = load_last_processed_entries()
  

    logging.info("Processing Hatena blogs")
    process_hatena_blogs(hatena_id, blog_domains, user_pass_tuple, output_file)
  


    #logging.info("Processing Qiita articles")
    #process_qiita_articles(qiita_token, last_processed_entries, output_file)

    with open(output_file, "r", encoding="utf-8") as f:
        text = f.read()
    deduplicated_text = remove_duplicates(text)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(deduplicated_text)

    save_last_processed_entries(last_processed_entries)

    logging.info(f"New article information has been added to the file '{output_file}'")
    logging.info("Script execution completed")