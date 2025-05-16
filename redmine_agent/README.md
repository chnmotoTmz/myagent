# Redmine チケット管理エージェント

Redmineのチケットを管理し、日次および週次レポートを自動生成するエージェントアプリケーション。
LINE botを通じて簡単にRedmineチケットの管理や作業時間の記録ができます。

## 機能

### 基本機能
- 朝の日次タスクレポート（9:00自動送信）
- 夕方の作業実績レポート（18:30自動送信）
- チケットのステータス更新
- 作業時間の記録
- 作業進捗率の更新
- チケット履歴の要約
- タスク効率化の提案

### AI支援機能（LLM連携）
- 自然言語コマンドの高度な解析
- チケットの緊急度評価と優先度分析
- 最適なチケット処理順序の提案
- チケットの次のアクションの提案
- 作業内容に基づいた日次サマリー生成

## セットアップ

### 前提条件

- Python 3.8+
- Redmine APIアクセス権限
- LINE Developer アカウント（LINE bot用）
- Google AI Studio アカウント（AI機能用、オプション）

### インストール

1. リポジトリのクローン
   ```
   git clone https://github.com/yourusername/redmine_agent.git
   cd redmine_agent
   ```

2. 仮想環境の作成と有効化
   ```
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate  # Windows
   ```

3. 依存ライブラリのインストール
   ```
   pip install -r requirements.txt
   ```

4. 設定ファイルの作成
   ```
   cp .env.sample .env
   ```
   
5. `.env` ファイルを編集して、Redmine、LINE botと必要に応じてGemini APIの認証情報を設定

```
# Redmine設定
REDMINE_URL=https://your-redmine-instance.com
REDMINE_API_KEY=your_redmine_api_key

# LINE Bot設定
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_token
LINE_CHANNEL_SECRET=your_line_channel_secret

# ユーザーIDマッピング (RedmineユーザーID => LINE ユーザーID)
USER_ID_MAPPING={"1":"Uxxxx...", "2":"Uyyyy..."}

# Google Gemini API設定 (AI機能用、オプション)
GEMINI_API_KEY=your_gemini_api_key

# 複数のAPIキーをローテーションする場合（オプション）
GEMINI_API_KEY1=your_first_api_key
GEMINI_API_KEY2=your_second_api_key
```

### Webhook URL設定

LINE Developer Console で Webhook URL を以下のように設定します：

```
https://your-server-address/api/webhook/line
```

## 使用方法

### アプリケーションの起動

```
python run.py
```

デフォルトでは、ポート8080でサーバーが起動します。

### APIステータスの確認

AI機能が正しく設定されているか確認するには：

```
python check_api.py
```

詳細なAI機能のセットアップと使用方法については `AI_FEATURES.md` を参照してください。

### LINEからの操作

以下のコマンドで操作できます：

#### 基本コマンド
- `/today` - 本日のタスク一覧
- `/tasks [日数]` - 今後のタスク一覧（デフォルト7日間）
- `/log <チケットID> <時間> <コメント>` - 作業時間を記録
- `/status <チケットID> <ステータスID> [コメント]` - ステータスを更新
- `/update <チケットID> <進捗率> [コメント]` - 進捗率を更新
- `/summary <チケットID>` - チケットの要約を表示
- `/report today` - 今日の作業レポート
- `/report week` - 週間サマリーレポート
- `/optimize` - タスク効率化の提案
- `/help` - ヘルプを表示

#### 自然言語コマンド（AI機能が有効な場合）
LLM統合が有効になっている場合、以下のような自然な言葉でも指示できます：

- 「今日のタスクを教えて」
- 「タスク123に2時間記録して、内容は顧客打ち合わせ」
- 「チケット456の進捗率を80%に更新して」
- 「タスク227のステータスを進行中に変更」
- 「効率的な作業順序を提案して」
- 「タスク789の詳細を教えて」
- `/report today` - 今日の作業レポート
- `/report week` - 週間サマリーレポート
- `/optimize` - タスク効率化の提案
- `/help` - ヘルプを表示

また、自然言語での指示も可能です。例：

- 「今日のタスク教えて」
- 「タスク135に2時間記録して、内容は打ち合わせ」
- 「週間レポートを見せて」

## RESTful API

以下のAPIエンドポイントも利用可能です：

- `GET /api/tasks/daily` - 本日のタスクを取得
- `GET /api/tasks/upcoming` - 今後のタスクを取得
- `GET /api/summary/{issue_id}` - チケットの要約を取得
- `GET /api/optimize` - タスク最適化の提案を取得
- `POST /api/time_entries` - 作業時間を登録
- `PUT /api/issues/{issue_id}` - チケットを更新
- `POST /api/send_morning_report` - 朝のレポートを手動送信（テスト用）
- `POST /api/send_evening_report` - 夜のレポートを手動送信（テスト用）

## ライセンス

MIT
