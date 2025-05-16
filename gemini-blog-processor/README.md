# Gemini Blog Processor

Gemini AIを活用してLINEメッセージや外部コンテンツからブログ記事の種を自動生成するFlaskアプリケーション

## 機能

- LINEメッセージの受信と処理
- 外部コンテンツのAPI経由での取り込み
- Gemini AIによるコンテンツの自動分析と記事案の生成
- ユーザー管理システム
- SQLiteデータベースによるデータ永続化
- Gemini Vision APIによる画像分析機能
- Redmineチケット管理エージェントとの連携

## 技術スタック

- Python 3.11
- Flask
- SQLAlchemy
- Google Cloud Gemini AI API
- Google Cloud Gemini Vision API
- LINE Messaging API
- Redmine API

## セットアップ

### 必要条件

- Python 3.11以上
- pip

### インストール

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
export GEMINI_API_KEY="your_api_key"
export GEMINI_VISION_API_KEY="your_vision_api_key"
export LINE_CHANNEL_SECRET="your_line_secret"
export LINE_CHANNEL_ACCESS_TOKEN="your_line_token"

# Redmine連携設定
REDMINE_API_URL=https://your-redmine-agent-api.com
REDMINE_API_KEY=your_api_key_here
REDMINE_TIMEOUT=30
REDMINE_INTEGRATION_ENABLED=True
```

## 使用方法

```bash
python src/main.py
```

デフォルトでは http://localhost:5000 でサーバーが起動します。
統合テスト用には http://localhost:8001 を使用します。

## API エンドポイント

### メッセージ処理
- `POST /api/receive_message` - A側からのメッセージ受信（画像分析対応）
- `GET /api/health` - ヘルスチェック

### LINE Webhook
- `POST /api/webhook/line` - LINEメッセージの受信
- `POST /api/webhook/trigger_process` - 記事生成の手動トリガー
- `GET /api/webhook/blog_seed/<hour_key>` - 生成された記事案の取得

### Redmine連携
- `POST /api/webhook/intent_process` - ブログ意図分析のRedmineへの転送
- `POST /api/webhook/blog_intent/forward_to_redmine/<hour_key>` - 特定の意図分析結果のRedmineへの転送

### ユーザー管理
- `GET /api/users` - ユーザー一覧の取得
- `POST /api/users` - 新規ユーザーの作成
- `GET /api/users/<id>` - 特定ユーザーの取得
- `PUT /api/users/<id>` - ユーザー情報の更新
- `DELETE /api/users/<id>` - ユーザーの削除

### 外部コンテンツ
- `POST /api/v1/external-content` - 外部コンテンツの受信

## 画像分析機能

このシステムはGemini Vision APIを使用して画像分析（image-to-text）を行います。
送信された画像は自動的に解析され、その内容が日本語で説明されます。
分析結果は自動的にブログ記事の案としてデータベースに保存され、
A側システムからhour_keyを指定して取得できます。

### 画像分析のポイント
- 日本語で詳細な画像説明を生成
- 主要な被写体、背景、人物、色彩などの特徴を分析
- 分析結果はMarkdown形式で保存

## Redmineチケット管理エージェントとの連携

Gemini Blog ProcessorはRedmineチケット管理エージェントと連携して、以下の機能を提供します：

### 機能概要
- LINEメッセージのRedmineチケット管理エージェントへの転送
- Redmineコマンド（@help, @create, @listなど）の処理
- ブログ意図分析結果のRedmineへの転送
- Redmineからの非同期処理ステータスの確認

### 連携エンドポイント
- `POST /api/webhook/intent_process` - ブログ意図分析のRedmineへの転送
- `POST /api/webhook/blog_intent/forward_to_redmine/<hour_key>` - 特定の意図分析結果のRedmineへの転送

### 設定
Redmine連携機能を使用するには、以下の環境変数を設定してください：

```bash
# Redmine連携設定
REDMINE_API_URL=https://your-redmine-agent-api.com
REDMINE_API_KEY=your_api_key_here
REDMINE_TIMEOUT=30
REDMINE_INTEGRATION_ENABLED=True
```

詳細なテスト手順は `docs/REDMINE_INTEGRATION_TEST.md` を参照してください。

## プロジェクト構造

```
src/
├── models/          # データベースモデル
├── routes/          # APIルート
├── static/          # 静的ファイル
├── database.py      # データベース設定
└── main.py         # アプリケーションのエントリーポイント
```

## 注意事項

- 本番環境では適切なセキュリティ設定を行ってください
- 機密情報は環境変数で管理してください
- 定期的にログのローテーションを行うことを推奨します

## ライセンス

MIT License