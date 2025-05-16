# Red-MCP

RedmineのためのModel Context Protocol (MCP) サーバー実装です。FastAPIを使用してRedmineとの連携を可能にします。

## 機能

- MCP準拠のツールマニフェストの提供
- Redmineでの課題（イシュー）作成

## 必要要件

- Python 3.7以上
- Redmineインスタンスとそのアクセス権

## インストール

1. リポジトリをクローンまたはダウンロードします。

2. 必要なパッケージをインストールします：

```bash
pip install -r requirements.txt
```

## 設定

環境変数または`config.py`で以下の設定が必要です：

- `REDMINE_API_KEY`: RedmineのAPIキー
- `REDMINE_URL`: RedmineサーバーのURL

環境変数での設定例：
```bash
export REDMINE_API_KEY="your-api-key"
export REDMINE_URL="https://your-redmine-url"
```

## サーバーの起動

```bash
uvicorn server:app --reload
```

サーバーは默認で`http://localhost:8000`で起動します。

## API エンドポイント

- `GET /tool/manifests`: 利用可能なツールのマニフェストを取得
- `POST /tool/create_issue`: 新しい課題を作成
- `GET /`: サーバーの状態確認
- `GET /docs`: API ドキュメント（Swagger UI）

## 使用例

新しい課題を作成する：

```bash
curl -X POST http://localhost:8000/tool/create_issue \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "project_id": 1,
      "subject": "テスト課題",
      "description": "これはテスト課題の説明です。"
    }
  }'
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。