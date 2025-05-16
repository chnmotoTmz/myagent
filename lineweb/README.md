# LineWeb Project

## 概要
このプロジェクトは、LINEメッセージを受信・処理し、コンテンツを管理・整理するシステムです。

## 主な機能

### メッセージ処理
- LINEメッセージの受信と自動処理
- テキスト、画像、動画メッセージの対応
- メッセージの要約機能
  - テキスト: 短文/長文の自動要約
  - 画像: ファイル情報の記録
  - 動画: ファイル情報の記録

### ファイル管理
- アップロードされたファイルの自動整理
- 年月ベースのディレクトリ構造
- ファイルタイプ別の分類（画像/動画/テキスト）
- バンドル機能（関連メッセージのグループ化）

### リトライ機構
- 失敗したメッセージの自動リトライ
- 指数バックオフによる再試行
- 失敗履歴の保存と管理

### データ永続化
- メッセージ要約の自動保存
- ユーザー別のデータ管理
- JSONベースのデータストレージ

## セットアップ

### 必要条件
- Python 3.12以上
- SQLite3

### インストール
```bash
pip install -r requirements.txt
```

### 環境変数の設定
`.env`ファイルを作成し、以下の環境変数を設定：
```
LINE_CHANNEL_SECRET=your-channel-secret
LINE_CHANNEL_ACCESS_TOKEN=your-channel-access-token
GOOGLE_API_KEY=your-google-api-key  # オプション: 画像分析機能用
```

## 起動方法

### Windowsでの起動
```bash
run.bat
```

### 手動での起動
```bash
python -m uvicorn line_webhook.app.main:app --reload --port 8083
```

## プロジェクト構造
```
lineweb/
├── line_webhook/            # メインアプリケーション
│   ├── app/                # アプリケーションコア
│   │   ├── main.py        # メインエントリーポイント
│   │   ├── summarizer.py  # メッセージ要約機能
│   │   ├── retry_queue.py # リトライ機構
│   │   └── organize_files.py # ファイル整理機能
│   └── tests/             # テストスイート
├── storage/               # データストレージ
│   ├── summaries/        # 要約データ
│   └── retry_queue/      # リトライキュー
└── logs/                 # ログファイル

