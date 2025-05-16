import re

def parse_blog_entries(text):
    entries = []
    current_entry = {}
    
    for line in text.split('\n'):
        if line.startswith("AUTHOR:"):
            if current_entry:
                entries.append(current_entry)
            current_entry = {"author": line[7:].strip(), "content": ""}
        elif line.startswith("BODY:"):
            current_entry["content"] += line[5:].strip() + " "
        elif not line.startswith("-----") and not any(line.startswith(field) for field in ["TITLE:", "STATUS:", "ALLOW COMMENTS:", "CONVERT BREAKS:", "ALLOW PINGS:", "PRIMARY CATEGORY:", "CATEGORY:", "DATE:", "EXTENDED BODY:", "EXCERPT:", "KEYWORDS:"]):
            current_entry["content"] += line.strip() + " "
    
    if current_entry:
        entries.append(current_entry)
    
    return entries

# テキストを読み込む
with open('1969681.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 記事を解析
entries = parse_blog_entries(text)

# 結果をファイルに出力
with open('output.txt', 'w', encoding='utf-8') as f:
    for entry in entries:
        # 内容の改行を全て削除
        content = re.sub(r'\s+', ' ', entry['content']).strip()
        f.write(f"{entry['author']}\t{content}\n")

print(f"{len(entries)}件の記事を output.txt に出力しました。")