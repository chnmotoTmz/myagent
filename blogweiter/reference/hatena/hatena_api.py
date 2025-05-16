# hatena_api.py

from hatena import load_credentials, retrieve_hatena_blog_entries, return_next_entry_list_uri

def get_blog_entries(hatena_id, blog_domain):
    user_pass_tuple = load_credentials(hatena_id)
    root_endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_domain}/atom"
    blog_entries_uri = f"{root_endpoint}/entry"
    entries = []

    while blog_entries_uri:
        entries_xml = retrieve_hatena_blog_entries(blog_entries_uri, user_pass_tuple)
        # ... XML解析処理 (参考ソースと同様)
        blog_entries_uri = return_next_entry_list_uri(links)
        # ... entry要素取得処理 (参考ソースと同様)

    return entries