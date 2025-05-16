@echo off
chcp 65001 > nul
echo LINE Webhook サーバーを起動しています...

rem 必要なパッケージが存在するか確認し、なければインストール
pip show httpx > nul 2>&1
if %errorlevel% neq 0 (
    echo httpx パッケージをインストールしています...
    pip install httpx
)

pip show line-bot-sdk > nul 2>&1
if %errorlevel% neq 0 (
    echo line-bot-sdk パッケージをインストールしています...
    pip install line-bot-sdk
)

rem Python スクリプトを実行して環境変数を読み込み、FastAPI アプリケーションを起動
python -c "import uvicorn; import os; from dotenv import load_dotenv; load_dotenv(); host = os.getenv('HOST', '0.0.0.0'); port = int(os.getenv('PORT', '8083')); uvicorn.run('line_webhook.app.main:app', host=host, port=port, reload=True)"

rem エラーがあれば表示して一時停止
if %errorlevel% neq 0 (
    echo エラーが発生しました。
    pause
)
