import requests
import json

url = "https://api.cohere.ai/v1/chat"
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": "bearer 3Pv7HYrARdBEkcNckSf0FNwp61I5Aife51XWxCWS"
}
data = {
    "chat_history": [
        {"role": "USER", "message": "あなたはスターダストレビューの根本要です"},
        {"role": "CHATBOT", "message": "はい、私は確かにスターダストレビューの根本要です。作曲のスキルもあります"}
    ],
    "message": "2000字でmichealjacjsonとコラボを想像して、テーマ曲を書いて、内容は春のハイキング。[Verse]/n冬の朝、目覚めたら/n白い雪が広がる大地 (うっとり)/n静寂に包まれた自然の中/n心躍る日常が始まる (きらきら)/n/n[Chorus]/n冬のハイキング、うきうき (うきうき)/n楽しい時間を過ごそう (過ごそう)/n共に歩いて、冒険の果て/n冬のワンダーランドへ (へいへい)/n/n[bridge]/n/n[intro]/n冬のワンダーランドへ (へいへい)/n/n[VERSE]/n冬の朝、目覚めたら/n白い雪が広がる大地 (うっとり)/n静寂に包まれた自然の中/n心躍る日常が始まる (きらきら)/n/n[Chorus]/n冬のハイキング、うきうき (うきうき)/n楽しい時間を過ごそう (過ごそう)/n共に歩いて、冒険の果て/n冬のワンダーランドへ (へいへい)",
    "connectors": [{"id": "web-search"}]
}

response = requests.post(url, headers=headers, data=json.dumps(data))

if response.status_code == 200:
    print(response.json())
else:
    print(f"Request failed with status code: {response.status_code}")