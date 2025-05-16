from dotenv import load_dotenv
import uvicorn
import os

def main():
    # .envファイルから環境変数を読み込み
    load_dotenv()
    
    # 環境変数から設定を読み込み
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8083'))
    
    # FastAPI アプリケーションを起動
    print(f"LINE Webhook サーバーを起動しています... (host={host}, port={port})")
    uvicorn.run('line_webhook.app.main:app', host=host, port=port, reload=True)

if __name__ == '__main__':
    main()