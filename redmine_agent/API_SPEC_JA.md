# Redmine チケット管理エージェント API仕様書

## 概要

この文書は、Redmine チケット管理エージェントの REST API 仕様を定義します。API を通じて、Redmine チケットの管理、作業時間の記録、レポートの生成などの機能にアクセスできます。

## ベース URL

```
https://your-server-address:8080
```

## 認証

現在、APIエンドポイントには特別な認証は実装されていません。実運用環境ではセキュリティ対策の実装を推奨します。

## レスポンス形式

すべてのAPIレスポンスはJSON形式で返されます。

成功時のレスポンス例:
```json
{
  "status": "ok",
  "message": "Operation successful"
}
```

エラー時のレスポンス例:
```json
{
  "detail": "エラーの詳細メッセージ"
}
```

## API エンドポイント一覧

### 基本エンドポイント

#### ヘルスチェック
- **URL**: `/`
- **メソッド**: `GET`
- **説明**: システムが正常に動作しているかを確認します
- **レスポンス例**:
  ```json
  {
    "status": "ok",
    "message": "Redmine Agent is running"
  }
  ```

### タスク管理

#### 本日のタスク取得
- **URL**: `/api/tasks/daily`
- **メソッド**: `GET`
- **パラメータ**:
  - `user_id` (オプション): Redmine ユーザーID
- **説明**: 本日のタスク一覧を取得します
- **レスポンス例**:
  ```json
  {
    "tasks": [
      {
        "id": 123,
        "subject": "タスク名",
        "status": {
          "id": 2,
          "name": "進行中"
        },
        "priority": {
          "id": 2,
          "name": "通常"
        },
        "due_date": "2025-05-16"
      }
    ]
  }
  ```

#### 今後のタスク取得
- **URL**: `/api/tasks/upcoming`
- **メソッド**: `GET`
- **パラメータ**:
  - `days` (オプション): 何日先までのタスクを取得するか (デフォルト: 7)
  - `user_id` (オプション): Redmine ユーザーID
- **説明**: 指定した期間内の予定タスクを取得します
- **レスポンス例**:
  ```json
  {
    "tasks": [
      {
        "id": 124,
        "subject": "タスク名",
        "status": {
          "id": 1,
          "name": "新規"
        },
        "priority": {
          "id": 2,
          "name": "通常"
        },
        "due_date": "2025-05-20"
      }
    ]
  }
  ```

#### チケット要約の取得
- **URL**: `/api/summary/{issue_id}`
- **メソッド**: `GET`
- **パラメータ**:
  - `issue_id`: チケットID (パスパラメータ)
- **説明**: 指定したチケットの詳細な要約を取得します
- **レスポンス例**:
  ```json
  {
    "subject": "タスク名",
    "status": "進行中",
    "done_ratio": 50,
    "estimated_hours": 8.0,
    "total_time_spent": 4.5,
    "recent_comments": [
      {
        "user": "ユーザー名",
        "date": "2025-05-15T14:30:00",
        "text": "コメント内容"
      }
    ]
  }
  ```

#### タスク最適化提案の取得
- **URL**: `/api/optimize`
- **メソッド**: `GET`
- **説明**: タスクの効率的な処理順序や統合の提案を取得します
- **レスポンス例**:
  ```json
  {
    "suggestions": [
      "類似タスクの統合提案",
      "効率的な作業順序の提案"
    ]
  }
  ```

#### チケット緊急度の分析 (LLM機能)
- **URL**: `/api/analyze/urgency/{issue_id}`
- **メソッド**: `GET`
- **パラメータ**:
  - `issue_id`: チケットID (パスパラメータ)
- **説明**: 指定したチケットの緊急度をAIで分析します
- **条件**: LLM機能が有効であること
- **レスポンス例**:
  ```json
  {
    "issue_id": 123,
    "subject": "タスク名",
    "status": "進行中",
    "priority": "通常",
    "urgency_analysis": {
      "score": 85,
      "reason": "締め切りが近く、依存するタスクが複数存在するため",
      "recommendation": "優先的に対応することを推奨"
    }
  }
  ```

### チケット更新

#### 作業時間の記録
- **URL**: `/api/time_entries`
- **メソッド**: `POST`
- **リクエストボディ**:
  ```json
  {
    "issue_id": 123,
    "hours": 2.5,
    "comments": "顧客との打ち合わせ",
    "spent_on": "2025-05-16"  // オプション
  }
  ```
- **説明**: チケットに対する作業時間を記録します
- **レスポンス例**:
  ```json
  {
    "status": "ok",
    "message": "Time entry created successfully"
  }
  ```

#### チケットの更新
- **URL**: `/api/issues/{issue_id}`
- **メソッド**: `PUT`
- **パラメータ**:
  - `issue_id`: チケットID (パスパラメータ)
- **リクエストボディ**:
  ```json
  {
    "status_id": 2,       // オプション: ステータスID
    "done_ratio": 50,     // オプション: 進捗率
    "notes": "進捗更新"  // オプション: コメント
  }
  ```
- **説明**: チケットのステータスや進捗率を更新します
- **レスポンス例**:
  ```json
  {
    "status": "ok",
    "message": "Issue updated successfully"
  }
  ```

### レポート

#### 朝のレポート送信 (テスト用)
- **URL**: `/api/send_morning_report`
- **メソッド**: `POST`
- **説明**: 朝のタスクレポートを手動で生成し、LINEを通じて送信します
- **レスポンス例**:
  ```json
  {
    "status": "ok",
    "message": "Morning reports scheduled"
  }
  ```

#### 夜のレポート送信 (テスト用)
- **URL**: `/api/send_evening_report`
- **メソッド**: `POST`
- **説明**: 夕方の作業実績レポートを手動で生成し、LINEを通じて送信します
- **レスポンス例**:
  ```json
  {
    "status": "ok",
    "message": "Evening reports scheduled"
  }
  ```

### LINE メッセージ

#### LINE Webhook
- **URL**: `/api/webhook/line`
- **メソッド**: `POST`
- **リクエストボディ**:
  ```json
  {
    "user": "LINE_USER_ID",
    "type": "text",
    "messageId": "message-id-12345",
    "message": "今日のタスクを教えて"
  }
  ```
- **説明**: LINE Botからのメッセージを処理します
- **レスポンス例**:
  ```json
  {
    "status": "ok",
    "message": "Message processed"
  }
  ```

#### 外部からのメッセージ受信
- **URL**: `/api/receive_message`
- **メソッド**: `POST`
- **リクエストボディ**:
  ```json
  {
    "user_id": "USER_ID",
    "content": "今日のタスクを教えて"
  }
  ```
- **説明**: 外部システムからのメッセージを受け取り、処理します
- **レスポンス例**:
  ```json
  {
    "status": "ok",
    "message": "Message processed successfully"
  }
  ```

### LLM (AI) 機能

#### LLM機能のステータス確認
- **URL**: `/api/llm/status`
- **メソッド**: `GET`
- **説明**: LLM（大規模言語モデル）機能の利用可否を確認します
- **レスポンス例**:
  ```json
  {
    "llm_available": true,
    "llm_ready": true,
    "api_connected": true,
    "api_keys_count": 2
  }
  ```

#### LLM機能の設定
- **URL**: `/api/llm/config`
- **メソッド**: `POST`
- **リクエストボディ**:
  ```json
  {
    "api_key": "your_gemini_api_key",
    "enable": true
  }
  ```
- **説明**: LLM機能のAPIキーを設定・更新します
- **レスポンス例**:
  ```json
  {
    "status": "success",
    "message": "APIキーの設定と接続テストに成功しました"
  }
  ```

### システム設定

#### 動作モードの変更
- **URL**: `/api/config/mode`
- **メソッド**: `POST`
- **リクエストボディ**:
  ```json
  {
    "mode": "dev"  // "dev" または "prod"
  }
  ```
- **説明**: システムの動作モード（開発モード/本番モード）を切り替えます
- **レスポンス例**:
  ```json
  {
    "status": "success",
    "message": "システム動作モードを 開発モード に変更しました",
    "mode": "dev",
    "debug": true
  }
  ```

## エラーコード

| ステータスコード | 説明 |
|------------|------|
| 400 | リクエストが不正 |
| 404 | リソースが見つからない |
| 500 | サーバー内部エラー |

## 備考

1. 本番環境で使用する場合は、適切な認証・認可の実装を検討してください。
2. モードの切り替え（開発モード/本番モード）によって一部の動作が変化します。
   - 開発モード: より詳細なログ出力、メッセージのシミュレーション
   - 本番モード: 実際のLINE API呼び出し、セキュリティ強化

3. LLM機能は、環境変数 `GEMINI_API_KEY` が設定され、必要なライブラリがインストールされている場合のみ利用可能です。
