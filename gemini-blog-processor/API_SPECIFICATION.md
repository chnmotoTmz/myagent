# Gemini Blog Processor API仕様書

## 概要
Gemini Blog Processor APIは、LINEや外部ソースからのテキストや画像データを受信し、Gemini AIを活用して分析・処理し、ブログコンテンツとして管理するためのインターフェースを提供します。

## 基本情報
- **ベースURL**: `http://localhost:8001/api`
- **認証方式**: APIキー認証（一部エンドポイントに必要）
- **レスポンス形式**: JSON
- **サーバー設定**: 環境変数（.envファイル）で管理

## エンドポイント一覧

### 1. メッセージ受信 API

#### リクエスト
- **URL**: `/receive_message`
- **メソッド**: `POST`
- **ヘッダ**:
  ```
  Content-Type: application/json
  ```
- **リクエストボディ**:
  ```json
  {
    "user_id": "ユーザーID",
    "message_id": "メッセージID",
    "message_type": "text|image|video",
    "content": "テキストメッセージの場合はテキスト内容",
    "filepath": "画像/動画メッセージの場合はファイルパス"
  }
  ```
- **必須パラメータ**:
  - `user_id`: メッセージを送信したユーザーのID
  - `message_id`: 一意のメッセージID
  - `message_type`: メッセージタイプ (`text`, `image`, `video`)
  - `filepath`または`content`: メッセージの内容（typeによる）

#### レスポンス
- **成功時** (202 Accepted):
  ```json
  {
    "status": "success",
    "message": "Message received and processing started",
    "message_id": "処理されたメッセージID",
    "received_at": "2025-05-16 13:45:22",
    "is_duplicate": false
  }
  ```
- **重複メッセージ時** (200 OK):
  ```json
  {
    "status": "success",
    "message": "Message already processed",
    "message_id": "処理されたメッセージID",
    "received_at": "2025-05-16 13:45:22",
    "is_duplicate": true
  }
  ```
- **バリデーションエラー時** (400 Bad Request):
  ```json
  {
    "status": "error",
    "message": "Missing required field: message_type"
  }
  ```
- **サーバーエラー時** (500 Internal Server Error):
  ```json
  {
    "status": "error",
    "message": "Internal server error: {詳細エラーメッセージ}"
  }
  ```

### 2. LINEウェブフック API

#### リクエスト
- **URL**: `/webhook/line`
- **メソッド**: `POST`
- **ヘッダ**:
  ```
  Content-Type: application/json
  X-Line-Signature: LINEからの署名
  ```
- **リクエストボディ**:
  LINEプラットフォームから送信されるイベントオブジェクト

#### レスポンス
- **成功時** (200 OK):
  ```json
  {
    "status": "success"
  }
  ```
- **署名検証エラー時** (401 Unauthorized):
  ```json
  {
    "status": "error",
    "message": "Invalid signature"
  }
  ```

### 3. ブログ記事取得 API

#### リクエスト
- **URL**: `/webhook/blog/<hour_key>`
- **メソッド**: `GET`
- **パスパラメータ**:
  - `hour_key`: ブログ記事の時間キー (形式: YYYYMMDDHHmm)

#### レスポンス
- **成功時** (200 OK):
  ```json
  {
    "status": "success",
    "data": {
      "hour_key": "202505161345",
      "markdown_content": "# ブログ記事タイトル\n\n記事内容...",
      "created_at": "2025-05-16T13:45:00+00:00",
      "updated_at": "2025-05-16T13:46:30+00:00"
    }
  }
  ```
- **記事が存在しない時** (404 Not Found):
  ```json
  {
    "status": "error",
    "message": "Blog seed not found for hour_key: 202505161345"
  }
  ```

### 4. 投稿意図分析 API

#### リクエスト
- **URL**: `/webhook/blog_intent/<hour_key>`
- **メソッド**: `GET` (既存の分析結果を取得) または `POST` (新規に分析を実行)
- **パスパラメータ**:
  - `hour_key`: ブログ記事の時間キー (形式: YYYYMMDDHHmm)

#### レスポンス (GET)
- **成功時** (200 OK):
  ```json
  {
    "status": "success",
    "data": {
      "id": 1,
      "hour_key": "202505161345",
      "intent_category": "比較分析",
      "intent_description": "U-NEXTとTVerの比較を通じて、U-NEXTの優位性を示し、利用を促進する",
      "confidence_score": 0.85,
      "target_audience": "動画配信サービス選びに迷っている一般ユーザー",
      "emotional_tone": "説得的",
      "call_to_action": "U-NEXTのより多様なコンテンツラインナップを検討する",
      "created_at": "2025-05-16T13:47:30+00:00",
      "updated_at": "2025-05-16T13:47:30+00:00"
    }
  }
  ```
- **分析結果が存在しない時** (404 Not Found):
  ```json
  {
    "status": "error",
    "message": "Intent analysis not found for hour_key: 202505161345"
  }
  ```

#### レスポンス (POST)
- **成功時** (201 Created):
  ```json
  {
    "status": "success",
    "message": "Intent analysis completed",
    "data": {
      "id": 1,
      "hour_key": "202505161345",
      "intent_category": "比較分析",
      "intent_description": "U-NEXTとTVerの比較を通じて、U-NEXTの優位性を示し、利用を促進する",
      "confidence_score": 0.85,
      "target_audience": "動画配信サービス選びに迷っている一般ユーザー",
      "emotional_tone": "説得的",
      "call_to_action": "U-NEXTのより多様なコンテンツラインナップを検討する",
      "created_at": "2025-05-16T13:47:30+00:00",
      "updated_at": "2025-05-16T13:47:30+00:00"
    }
  }
  ```
- **分析エラー時** (500 Internal Server Error):
  ```json
  {
    "status": "error",
    "message": "Failed to analyze intent for hour_key: 202505161345"
  }
  ```
- **元記事が存在しない時** (404 Not Found):
  ```json
  {
    "status": "error",
    "message": "Blog seed not found for hour_key: 202505161345"
  }
  ```

### 5. 外部コンテンツ取込 API

#### リクエスト
- **URL**: `/external-content`
- **メソッド**: `POST`
- **ヘッダ**:
  ```
  Content-Type: application/json
  X-API-Key: APIキー
  ```
- **リクエストボディ**:
  ```json
  {
    "content_id": "コンテンツID",
    "source_type": "rss|twitter|other",
    "title": "コンテンツタイトル",
    "content": "コンテンツ本文",
    "url": "コンテンツのURL",
    "metadata": {
      "author": "著者名",
      "published_at": "発行日時",
      "tags": ["タグ1", "タグ2"]
    }
  }
  ```

#### レスポンス
- **成功時** (202 Accepted):
  ```json
  {
    "status": "success",
    "message": "Data received successfully.",
    "received_content_id": "処理されたコンテンツID"
  }
  ```
- **認証エラー時** (401 Unauthorized):
  ```json
  {
    "status": "error",
    "message": "Invalid API key"
  }
  ```
- **バリデーションエラー時** (400 Bad Request):
  ```json
  {
    "status": "error",
    "message": "Missing required field: content"
  }
  ```

### 6. ヘルスチェック API

#### リクエスト
- **URL**: `/health`
- **メソッド**: `GET`

#### レスポンス
- **成功時** (200 OK):
  ```json
  {
    "status": "ok"
  }
  ```

## データモデル

### Message
メッセージ情報を保存するモデル
```json
{
  "message_id": "メッセージID (主キー)",
  "user_id": "ユーザーID",
  "message_type": "メッセージタイプ (text|image|video)",
  "content": "メッセージ内容またはファイルパス",
  "timestamp": "受信時刻 (UTC)"
}
```

### BlogSeed
ブログ記事の元データを保存するモデル
```json
{
  "hour_key": "時間キー (主キー, YYYYMMDDHHmm形式)",
  "markdown_content": "マークダウン形式のブログ記事内容",
  "created_at": "作成時刻 (UTC)",
  "updated_at": "更新時刻 (UTC)"
}
```

### BlogIntentAnalysis
ブログ記事の意図分析結果を保存するモデル
```json
{
  "id": "ID (主キー, 自動採番)",
  "hour_key": "関連するブログ記事の時間キー (外部キー)",
  "intent_category": "意図カテゴリ",
  "intent_description": "意図の詳細説明",
  "confidence_score": "確信度 (0.0～1.0)",
  "target_audience": "対象読者",
  "emotional_tone": "感情的トーン",
  "call_to_action": "行動喚起内容",
  "raw_response": "Gemini APIからの生の応答",
  "created_at": "作成時刻 (UTC)",
  "updated_at": "更新時刻 (UTC)"
}
```

### User
ユーザー情報を保存するモデル
```json
{
  "user_id": "ユーザーID (主キー)",
  "username": "ユーザー名",
  "email": "メールアドレス",
  "created_at": "作成時刻 (UTC)",
  "last_active": "最終アクティブ時刻 (UTC)"
}
```

## 認証とセキュリティ

### APIキー認証
一部エンドポイント（external-content等）はAPIキーによる認証が必要です。APIキーはヘッダー`X-API-Key`で送信する必要があります。

### IP制限
デフォルトでは以下のIPアドレスからのアクセスのみが許可されています：
- 127.0.0.1
- localhost
- ::1

### LINE署名検証
LINEウェブフックエンドポイントはLINEプラットフォームからの署名検証を実施します。

## Gemini API設定

投稿意図分析APIでは、以下の設定でGemini APIを使用しています：

- **モデル**: gemini-2.5-flash-preview-04-17
- **Temperature**: 1.0（クリエイティブな出力）
- **Candidate Count**: 1
- **Timeout**: 60秒（環境変数で設定可能）

## エラーコード

| HTTPステータス | 説明 |
|--------------|------|
| 200 OK | リクエストは成功し、結果が返されました |
| 201 Created | リソースが新規に作成されました |
| 202 Accepted | リクエストは受け付けられましたが、処理は非同期で実行されます |
| 400 Bad Request | リクエストの形式が不正です |
| 401 Unauthorized | 認証に失敗しました |
| 403 Forbidden | 認証されましたが、アクセス権がありません |
| 404 Not Found | 要求されたリソースが見つかりません |
| 500 Internal Server Error | サーバー内部でエラーが発生しました |

## 使用上の注意事項

1. 時間キー（hour_key）は5分刻みで生成されます（例：202505161345）
2. メッセージ処理は非同期で行われます。メッセージ受信APIは受信確認のみを返し、処理結果は別途取得する必要があります
3. 画像処理にはGemini Vision APIを使用しています
4. 環境変数の設定は`.env`ファイルで管理されています
5. すべての日時はUTC形式で保存・返却されます

## 環境設定

環境変数は`.env`ファイルで設定します。主な設定項目は以下の通りです：

```
# Gemini API設定
GEMINI_API_KEY=xxxxxxxxxxxxx
GEMINI_TIMEOUT=60

# データベース設定
DATABASE_URL=sqlite:///instance/app.db

# サーバー設定
PORT=8001
DEBUG=True
SECRET_KEY=xxxxxxxxxxx

# 外部サービス連携設定
LINE_WEBHOOK_URL=http://localhost:8083/webhook
RETRY_MAX_ATTEMPTS=3
RETRY_DELAY_SECONDS=5

# ログ設定
LOG_LEVEL=DEBUG
```

## バージョン情報

- 最終更新日: 2025年5月16日
- バージョン: 1.0.0

---

*本API仕様書はGemini Blog Processor開発チームによって提供されています。*
