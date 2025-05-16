import requests

access_token = "ee807f726eb74be225a715f2514a81acc8377e1b"
headers = {'Authorization': f'Bearer {access_token}'}
page = 1
per_page = 100  # 1ページあたりの取得数

all_articles = []

while True:
    url = f'https://qiita.com/api/v2/authenticated_user/items?page={page}&per_page={per_page}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        articles = response.json()
        if not articles:
            break  # 記事が取得できなくなったら終了
        all_articles.extend(articles)
        page += 1
    else:
        print(f'Error: {response.status_code}')
        break

for article in all_articles:
    print(f'Title: {article["title"]}, URL: {article["url"]}')
    