# main.py

from config import *
from hatena_api import get_blog_entries
from article_updater import update_article
from hatena_poster import post_to_hatena

def main():
    for account in HATENA_BLOG_ACCOUNTS:
        blog_entries = get_blog_entries(account["hatena_id"], account["blog_domain"])
        for entry in blog_entries[:MAX_BLOGS_PER_ACCOUNT]:
            updated_entry = update_article(entry)
            post_to_hatena(updated_entry, account)

if __name__ == "__main__":
    main()