# Gemini Blog Processor と Redmineチケット管理システムの連携仕様書

## 概要

本文書は、Gemini Blog Processor（B側）とRedmineチケット管理エージェント（A側）の連携仕様を定義します。両システムはそれぞれのAPIを介して通信し、データの受け渡しを行います。

## システム構成

### Redmineチケット管理エージェント（A側）
- Redmineチケット管理、作業時間記録、レポート生成機能を提供
- REST APIベースのシステム
- Gemini APIによる自然言語処理機能を実装

### Gemini Blog Processor（B側）
- LINEなどからのメッセージを受信し、Gemini AIで処理
- ブログコンテンツの生成と管理
- 投稿意図分析機能を実装

## 連携方式

### 1. 相互メッセージング連携

#### B側からA側への連携:

1. **タスク関連のブログコンテンツ検出時**
   - B側の`BlogIntentAnalysis`でタスク関連のコンテンツと判断された場合、A側の`/receive_message`エンドポイントにデータを送信

2. **リクエスト例**:
   ```json
   {
     "user_id": "U0082f5630775769cb2655fb503e958bb",
     "message_id": "blog-intent-20250516-001",
     "message_type": "text",
     "content": "@task 新しいブログ記事「U-NEXTとTVerの比較」の作成をタスクに追加してください"
   }
   ```

#### A側からB側への連携:

1. **タスク完了時の記事生成リクエスト**
   - A側でタスク完了時にB側の`/api/receive_message`エンドポイントに記事生成リクエストを送信

2. **リクエスト例**:
   ```json
   {
     "user_id": "redmine-system",
     "message_id": "task-completion-20250516-001",
     "message_type": "text",
     "content": "タスク#1234「U-NEXTとTVerの比較記事の作成」が完了しました。以下の内容を元に記事を生成してください：\n\n- U-NEXTは月額料金が高いが、コンテンツが豊富\n- TVerは無料だが、配信期間が限定的\n- ..."
   }
   ```

### 2. コマンド連携

#### Gemini Blog Processor（B側）が対応するRedmine連携コマンド:

1. **`@today`** - 本日のタスク一覧を表示
   - B側でこのコマンドを検出した場合、A側の`/tasks/daily`エンドポイントにリクエストし、結果をブログ記事に含める

2. **`@tasks`** - 今後のタスク一覧を表示
   - B側でこのコマンドを検出した場合、A側の`/tasks/upcoming`エンドポイントにリクエストし、結果をブログ記事に含める

3. **`@log <チケットID> <時間> <コメント>`** - 作業時間を記録
   - B側でこのコマンドを検出した場合、A側の`/time_entries`エンドポイントにリクエストし、作業時間を記録

4. **`@summary <チケットID>`** - チケット要約の取得
   - B側でこのコマンドを検出した場合、A側の`/summary/{issue_id}`エンドポイントにリクエストし、要約をブログ記事に含める

### 3. 画像/メディア連携

1. **タスク関連の画像送信**
   - B側で受信した画像がタスクに関連すると判断された場合、A側の`/receive_message`エンドポイントに転送

2. **リクエスト例**:
   ```json
   {
     "user_id": "U0082f5630775769cb2655fb503e958bb",
     "message_id": "image-task-20250516-001",
     "message_type": "image",
     "filepath": "C:\\Users\\Public\\Documents\\U0082f5630775769cb2655fb503e958bb\\20250516_133245_875421.jpg"
   }
   ```

## 連携の実装方法

### 1. コマンド検出機能の追加

B側のメッセージ処理部分（`process_message_async`関数）に、Redmineコマンド検出機能を追加します：

```python
# Redmineコマンドを検出する関数
def detect_redmine_commands(text_content: str) -> Optional[Dict]:
    """テキスト内のRedmineコマンドを検出する
    
    Args:
        text_content: 検査対象のテキスト
        
    Returns:
        コマンド情報を含む辞書、コマンドがない場合はNone
    """
    if not text_content:
        return None
        
    # @todayコマンドの検出
    if "@today" in text_content.lower():
        return {"command": "today", "params": {}}
        
    # @tasksコマンドの検出
    if "@tasks" in text_content.lower():
        return {"command": "tasks", "params": {}}
        
    # @logコマンドの検出
    log_pattern = r"@log\s+#?(\d+)\s+(\d+(?:\.\d+)?)\s+(.+)"
    log_match = re.search(log_pattern, text_content)
    if log_match:
        return {
            "command": "log",
            "params": {
                "issue_id": log_match.group(1),
                "hours": log_match.group(2),
                "comment": log_match.group(3).strip()
            }
        }
        
    # @summaryコマンドの検出
    summary_pattern = r"@summary\s+#?(\d+)"
    summary_match = re.search(summary_pattern, text_content)
    if summary_match:
        return {
            "command": "summary",
            "params": {
                "issue_id": summary_match.group(1)
            }
        }
    
    return None
```

### 2. Redmine API連携クラスの実装

A側システムと通信するためのクラスを実装します：

```python
class RedmineIntegration:
    """Redmineチケット管理システム(A側)と連携するクラス"""
    
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": api_key
        })
        
    def send_message(self, message_data: Dict) -> Dict:
        """A側の/receive_messageエンドポイントにメッセージを送信"""
        url = f"{self.base_url}/receive_message"
        response = self.session.post(url, json=message_data)
        response.raise_for_status()
        return response.json()
        
    def get_daily_tasks(self) -> Dict:
        """本日のタスク一覧を取得"""
        url = f"{self.base_url}/tasks/daily"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
        
    def get_upcoming_tasks(self) -> Dict:
        """今後のタスク一覧を取得"""
        url = f"{self.base_url}/tasks/upcoming"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
        
    def log_time_entry(self, issue_id: str, hours: str, comment: str) -> Dict:
        """作業時間を記録"""
        url = f"{self.base_url}/time_entries"
        data = {
            "issue_id": issue_id,
            "hours": float(hours),
            "comment": comment
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
        
    def get_issue_summary(self, issue_id: str) -> Dict:
        """チケット要約を取得"""
        url = f"{self.base_url}/summary/{issue_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
```

### 3. 設定ファイルの更新

`config.py`に以下の設定を追加します：

```python
# Redmine連携設定
REDMINE_API_BASE_URL = os.environ.get("REDMINE_API_BASE_URL", "http://localhost:8002/api")
REDMINE_API_KEY = os.environ.get("REDMINE_API_KEY", "")
REDMINE_INTEGRATION_ENABLED = os.environ.get("REDMINE_INTEGRATION_ENABLED", "False").lower() in ("true", "1", "t")
```

`.env`ファイルにも対応する設定を追加：

```
# Redmine連携設定
REDMINE_API_BASE_URL=http://localhost:8002/api
REDMINE_API_KEY=your_redmine_api_key_here
REDMINE_INTEGRATION_ENABLED=True
```

## エラーハンドリング

1. **接続エラー**
   - A側システムが応答しない場合は、ログに記録し、エラーメッセージをユーザーに返す
   - 重要なリクエストは再試行キューに入れ、後で再試行

2. **認証エラー**
   - API認証が失敗した場合は、ログに記録し、システム管理者に通知

3. **不正なレスポンス**
   - 予期しないフォーマットのレスポンスを受け取った場合、安全なフォールバック処理を行う

## セキュリティ考慮事項

1. **認証**: 相互のAPIリクエストにはAPIキーを使用し、通信を保護
2. **データ検証**: 送受信するデータに対して厳密な検証を実施
3. **機密情報**: ユーザーIDなどの機密情報は適切に保護
4. **アクセス制限**: IPアドレス制限を実装し、許可されたシステム間のみの通信を許可

## 今後の拡張可能性

1. **双方向のリアルタイム通知**
   - WebSocketを使用したリアルタイム通知システムの実装

2. **ブログコンテンツからのタスク自動生成**
   - ブログコンテンツの分析結果からRedmineタスクを自動生成

3. **タスク進捗の可視化**
   - ブログ形式でのタスク進捗レポート自動生成

4. **データ同期の強化**
   - 定期的なデータ同期バッチ処理の追加

---

本連携仕様書は、両システムのAPI仕様に基づいて作成されています。実際の実装にあたっては、セキュリティとスケーラビリティに十分な配慮が必要です。また、両システムの変更に応じて、本仕様書も適宜更新する必要があります。
