# Ameba Blog Manager

アメーバブログの記事を効率的に管理するためのPythonアプリケーションです。

## 主な機能

- ブログ記事の一覧取得と管理
- 記事のインポートとエクスポート
- JSONフォーマットでの記事保存
- ローカルでの記事管理
- GUIインターフェース

## 必要要件

- Python 3.8以上
- Google Chrome
- ChromeDriver

## インストール

1. リポジトリをクローン：
```bash
git clone https://github.com/yourusername/ameba.git
cd ameba
```

2. 必要なパッケージをインストール：
```bash
pip install -r requirements.txt
```

3. 環境変数の設定：
`.env`ファイルを作成し、以下の内容を設定：
```
AMEBA_USERNAME=あなたのアメーバID
AMEBA_PASSWORD=あなたのパスワード
```

## 使用方法

### GUIアプリケーションの起動

```bash
python ameba_gui.py
```

### ブラウザの準備

1. Chromeブラウザをデバッグモードで起動：
```bash
chrome.exe --remote-debugging-port=9222
```

### 記事の管理

1. 記事一覧の取得
   - 「記事取得」ボタンをクリック
   - リモート記事タブに記事一覧が表示されます

2. 記事のインポート
   - インポートしたい記事を選択
   - 「インポート」ボタンをクリック

3. 記事のエクスポート
   - エクスポートしたい記事を選択
   - 「JSONエクスポート」ボタンをクリック
   - 指定したフォーマットでJSONファイルが生成されます

## プロジェクト構成

```
ameba/
├── ameba_gui.py              # メインGUIアプリケーション
├── ameba_automation/
│   ├── __init__.py
│   ├── browser_automation.py # ブラウザ自動化
│   ├── config.py            # 設定管理
│   ├── database.py          # データベース操作
│   ├── exceptions.py        # 例外定義
│   ├── gui_app.py          # GUIコンポーネント
│   ├── main.py             # メインロジック
│   ├── rss_fetcher.py      # RSSフィード取得
│   └── utils.py            # ユーティリティ関数
└── tests/                   # テストコード
```

## エラー対処

### Chromeが見つからない場合
- すべてのChromeウィンドウを閉じる
- コマンドプロンプトで以下を実行：
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

### ログインできない場合
- 環境変数（.env）の設定を確認
- Chromeを再起動して再試行

## 開発者向け情報

### テストの実行

```bash
python -m unittest discover tests
```

### 新しい記事フォーマットの追加

`post_converter.py`を使用して、新しい記事フォーマットを追加できます：

```python
from ameba_automation.database import AmebaDatabase
from ameba_automation.post_converter import PostConverter

db = AmebaDatabase()
converter = PostConverter(db)

# 記事をJSONに変換
json_data = converter.convert_post("記事ID")

# JSONファイルとして保存
converter.save_as_json("記事ID", "output.json")
```

## ライセンス

MITライセンス

## 作者

[あなたの名前]

## 貢献

1. Fork it
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create new Pull Request
