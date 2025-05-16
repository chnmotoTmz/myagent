from flask import Flask, redirect, url_for, session
from flask_dance.contrib.facebook import make_facebook_blueprint, facebook
import pdb

app = Flask(__name__)
app.secret_key = "your-secret-key"  # 重要: 必ず安全な値を設定してください



facebook_bp = make_facebook_blueprint(
    client_id= '721757868690995',
    client_secret = 'fa411272ea77e12c82cc8767e9e4b266',
)


app.register_blueprint(facebook_bp, url_prefix="/login")

@app.route("/")
def index():
    if not facebook.authorized:
        return redirect(url_for("facebook.login"))
    
    # セッションからアクセストークンを取得
    pdb.set_trace()
    
    access_token = facebook.access_token

    graph = facebook.GraphAPI(access_token)
    profile = graph.get('me?fields=name,email')
    print(profile)
    return f"You are {profile['name']}!"

