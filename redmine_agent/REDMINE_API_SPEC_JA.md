# Redmine API連携仕様書

## 概要

この文書は、Redmine チケット管理エージェントと Redmine API の連携仕様を定義します。Redmine チケット管理エージェントは、Redmine APIを使用してチケットの取得、更新、作業時間の記録などを行います。

## Redmine APIの基本情報

### ベースURL

```
https://your-redmine-instance.com
```

### 認証

Redmine APIへのすべてのリクエストには、APIキーによる認証が必要です。

```
X-Redmine-API-Key: your_redmine_api_key
```

APIキーは環境変数 `REDMINE_API_KEY` で設定します。

### レスポンス形式

すべてのRedmine APIレスポンスはJSON形式で返されます。

## 使用する主なAPI

### 1. チケット（Issues）

#### チケット一覧の取得

- **URL**: `/issues.json`
- **メソッド**: `GET`
- **主なパラメータ**:
  - `status_id`: チケットのステータスID（"open" で進行中のチケットを指定）
  - `assigned_to_id`: 担当者ID
  - `sort`: ソート順（例: `priority:desc,due_date:asc`）
  - `limit`: 取得する最大件数
  - `due_date`: 期限日（演算子付き。例: `<=2025-05-20`）
  - `start_date`: 開始日（演算子付き）
- **使用例**:
  ```python
  # 本日のタスクを取得する例
  params = {
      "status_id": "open",
      "sort": "priority:desc,due_date:asc",
      "limit": 100
  }
  
  if user_id:
      params["assigned_to_id"] = user_id
  
  response = requests.get(
      f"{self.redmine_url}/issues.json",
      headers=self.headers,
      params=params
  )
  ```

#### 特定チケットの取得

- **URL**: `/issues/{issue_id}.json`
- **メソッド**: `GET`
- **パラメータ**:
  - `issue_id`: チケットID（パスパラメータ）
  - `include`: 関連情報を含める（attachments, relations, journals など）
- **使用例**:
  ```python
  response = requests.get(
      f"{self.redmine_url}/issues/{issue_id}.json",
      headers=self.headers
  )
  ```

#### チケットのステータス更新

- **URL**: `/issues/{issue_id}.json`
- **メソッド**: `PUT`
- **パラメータ**:
  - `issue_id`: チケットID（パスパラメータ）
- **リクエストボディ**:
  ```json
  {
    "issue": {
      "status_id": 2,
      "notes": "ステータスを更新しました"
    }
  }
  ```
- **使用例**:
  ```python
  data = {
      "issue": {
          "status_id": status_id
      }
  }
  
  if notes:
      data["issue"]["notes"] = notes
  
  response = requests.put(
      f"{self.redmine_url}/issues/{issue_id}.json",
      headers=self.headers,
      json=data
  )
  ```

#### チケットの進捗率更新

- **URL**: `/issues/{issue_id}.json`
- **メソッド**: `PUT`
- **パラメータ**:
  - `issue_id`: チケットID（パスパラメータ）
- **リクエストボディ**:
  ```json
  {
    "issue": {
      "done_ratio": 50,
      "notes": "進捗率を更新しました"
    }
  }
  ```
- **使用例**:
  ```python
  data = {
      "issue": {
          "done_ratio": done_ratio
      }
  }
  
  if notes:
      data["issue"]["notes"] = notes
  
  response = requests.put(
      f"{self.redmine_url}/issues/{issue_id}.json",
      headers=self.headers,
      json=data
  )
  ```

### 2. 作業時間（Time Entries）

#### 作業時間の記録

- **URL**: `/time_entries.json`
- **メソッド**: `POST`
- **リクエストボディ**:
  ```json
  {
    "time_entry": {
      "issue_id": 123,
      "hours": 2.5,
      "comments": "作業内容の説明",
      "spent_on": "2025-05-16",
      "activity_id": 4
    }
  }
  ```
- **使用例**:
  ```python
  data = {
      "time_entry": {
          "issue_id": issue_id,
          "hours": hours,
          "comments": comments,
          "spent_on": spent_on,
          "activity_id": 4  # アクティビティID（タスク）
      }
  }
  
  response = requests.post(
      f"{self.redmine_url}/time_entries.json",
      headers=self.headers,
      json=data
  )
  ```

#### 作業時間の取得

- **URL**: `/time_entries.json`
- **メソッド**: `GET`
- **主なパラメータ**:
  - `issue_id`: チケットID
  - `user_id`: ユーザーID
  - `from`: 開始日 (YYYY-MM-DD形式)
  - `to`: 終了日 (YYYY-MM-DD形式)
  - `limit`: 取得する最大件数
- **使用例**:
  ```python
  params = {
      "limit": 100
  }
  
  if issue_id:
      params["issue_id"] = issue_id
  
  if from_date:
      params["from"] = from_date
  
  if to_date:
      params["to"] = to_date
  
  if user_id:
      params["user_id"] = user_id
  
  response = requests.get(
      f"{self.redmine_url}/time_entries.json",
      headers=self.headers,
      params=params
  )
  ```

### 3. その他のAPI

#### プロジェクト一覧

- **URL**: `/projects.json`
- **メソッド**: `GET`
- **使用例**:
  ```python
  response = requests.get(
      f"{self.redmine_url}/projects.json",
      headers=self.headers
  )
  ```

#### ステータス一覧

- **URL**: `/issue_statuses.json`
- **メソッド**: `GET`
- **使用例**:
  ```python
  response = requests.get(
      f"{self.redmine_url}/issue_statuses.json",
      headers=self.headers
  )
  ```

#### 優先度一覧

- **URL**: `/enumerations/issue_priorities.json`
- **メソッド**: `GET`
- **使用例**:
  ```python
  response = requests.get(
      f"{self.redmine_url}/enumerations/issue_priorities.json",
      headers=self.headers
  )
  ```

## APIアクセスのベストプラクティス

### エラーハンドリング

すべてのAPI呼び出しに対して、適切なエラーハンドリングを実装してください。

```python
try:
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # 4xx/5xxエラーの場合は例外を発生
    data = response.json()
    # 以降、データの処理
except requests.exceptions.RequestException as e:
    logger.error(f"API request failed: {e}")
    # エラー処理
```

### レート制限への対応

Redmine APIにはレート制限がある場合があります。同じエンドポイントへの頻繁なリクエストは避け、必要に応じてキャッシュを使用してください。

### 認証情報の保護

APIキーは機密情報として扱い、ソースコードにハードコードせず環境変数などで管理してください。

## 環境設定

### 必要な環境変数

- `REDMINE_URL`: Redmine インスタンスのベースURL
- `REDMINE_API_KEY`: Redmine APIアクセス用のAPIキー

### 設定例

```
# Redmine設定
REDMINE_URL=https://your-redmine-instance.com
REDMINE_API_KEY=your_redmine_api_key
```

## 開発モードと本番モード

Redmine APIの呼び出しは開発モードと本番モードで以下のように動作が異なります：

### 開発モード
- 実際にAPIを呼び出すが、詳細なログ出力を行います
- レスポンスの詳細をデバッグレベルでログに記録します

### 本番モード
- 実際にAPIを呼び出し、必要最小限のログ出力のみ行います
- エラー時のみ詳細をログに記録します

## 仕様に関する注意事項

1. Redmine APIのバージョンによって利用可能なエンドポイントや必須パラメータが異なる場合があります。
2. カスタムフィールドを使用している場合は、それぞれのフィールドID（`cf_1`など）での指定が必要です。
3. 日付は基本的に ISO 8601 形式（YYYY-MM-DD）で指定します。
4. 期間指定には演算子（`>=`, `<=`, `><`）が使用できます。
