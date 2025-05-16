import facebook

# アプリIDとApp Secretを設定
app_id = '721757868690995'
app_secret = 'fa411272ea77e12c82cc8767e9e4b266'

from flask import Flask, redirect, url_for, session
from flask_dance.contrib.facebook import make_facebook_blueprint, facebook

app = Flask(__name__)
app.secret_key = "your-secret-key"  # 重要: 必ず安全な値を設定してください

facebook_bp = make_facebook_blueprint(
    client_id="your-app-id",
    client_secret="your-app-secret",
)
app.register_blueprint(facebook_bp, url_prefix="/login")

@app.route("/")
def index():
    if not facebook.authorized:
        return redirect(url_for("facebook.login"))
    
    # セッションからアクセストークンを取得
    access_token = facebook.access_token

    graph = facebook.GraphAPI(access_token)
    profile = graph.get('me?fields=name,email')
    print(profile)

    return f"You are {profile['name']}!"