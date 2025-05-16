# article_updater.py

from cohere_api import generate_summary, extract_keywords
from rakuten_api import search_products, generate_affiliate_link
from image_generator import generate_image_from_prompt
from utils import find_internal_links

def update_article(entry):
    # 1. AIによる記事リライト (2000文字以上)
    updated_content = generate_summary(entry["content"], length="long")

    # 2. 主要語句の抽出とアフィリエイトリンク生成
    keywords = extract_keywords(updated_content, num_keywords=10)
    for keyword in keywords:
        products = search_products(keyword)
        if products:
            affiliate_link = generate_affiliate_link(products[0]["itemCode"])
            updated_content = updated_content.replace(
                keyword, f'<a href="{affiliate_link}">{keyword}</a>'
            )

    # 3. 同サイト内の類似テーマ記事へのリンク挿入
    internal_links = find_internal_links(updated_content, entry["url"])
    for link in internal_links:
        updated_content += f'<a href="{link}">{link}</a>'

    # 4. 画像プロンプトに基づく画像の挿入
    image_url = generate_image_from_prompt(entry["image_prompt"])
    updated_content += f'<img src="{image_url}" alt="{entry["title"]}">'

    # 5. 記事情報の更新
    entry["content"] = updated_content

    return entry