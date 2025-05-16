# EasyRAG-v2

## 概要

EasyRAG-v2は、Retrieval-Augmented Generation (RAG) を用いたアプリケーションのプロトタイプです。
フロントエンドはHTML, CSS, JavaScriptで構築され、バックエンドはPythonで構築されています。

## 使用技術

- フロントエンド: HTML, CSS, JavaScript, Tailwind CSS, Vite
- バックエンド: Python

## セットアップ方法

### フロントエンド

1. `frontend` ディレクトリに移動します。
2. `npm install` を実行して依存関係をインストールします。
3. `npm run dev` を実行して開発サーバーを起動します。

### バックエンド

1. `backend` ディレクトリに移動します。
2. 仮想環境を作成します (例: `python3 -m venv .venv`)。
3. 仮想環境をアクティベートします (例: `source .venv/bin/activate`)。
4. `pip install -r requirements.txt` を実行して依存関係をインストールします。
5. `python main.py` を実行してアプリケーションを起動します。

## ディレクトリ構成

- `frontend`: フロントエンド関連のファイルが格納されています。
  - `public`: 静的ファイルが格納されています。
    - `css`: CSSファイルが格納されています。
    - `js`: JavaScriptファイルが格納されています。
- `backend`: バックエンド関連のファイルが格納されています。
  - `initialize_hatena.py`: はてなブログ関連の初期化スクリプトです。
  - `main.py`: メインのアプリケーションスクリプトです。
  - `logs`: ログファイルが格納されています。
  - `models`: データモデル関連のファイルが格納されています。
  - `routers`: ルーティング関連のファイルが格納されています。
  - `services`: サービス関連のファイルが格納されています。

## 備考

- 詳細な手順や設定については、各ディレクトリ内のREADMEやドキュメントを参照してください。
