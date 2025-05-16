import requests
import urllib.parse


def generate_rakuten_affiliate_link(keyword):
    # APIのベースURL
    base_url = "https://app.rakuten.co.jp/services/api/Product/Search/20170426"
    
    # あなたの Application ID と Affiliate ID
    app_id = "1085678693500866208"
    affiliate_id = "1feccffa.7c7bccd7.1feccffb.111f7d7e"
    
    # パラメータの設定
    params = {
        "format": "json",
        "applicationId": app_id,
        "keyword": keyword,
        "hits": 1  # 最初の1件のみ取得
    }
    
    # APIリクエスト
    response = requests.get(base_url, params=params)
    data = response.json()
    
    if "Products" in data and len(data["Products"]) > 0:
        product = data["Products"][0]["Product"]
        
        # 商品情報の取得
        product_name = product["productName"]
        product_url = product["productUrlPC"]
        
        # PCとモバイル用のURLを作成
        pc_url = urllib.parse.quote(product_url)
        mobile_url = urllib.parse.quote(product_url.replace('https://product.rakuten.co.jp', 'https://product.rakuten.co.jp/m'))
        
        # アフィリエイトリンクを生成
        affiliate_url = f"http://hb.afl.rakuten.co.jp/hgc/{affiliate_id}/?pc={pc_url}&m={mobile_url}"
        
        # HTMLリンクを生成
        html_link = f'<a href="{affiliate_url}" target="_blank">{product_name}</a>'
        
        return html_link
    else:
        return None
