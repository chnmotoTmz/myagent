# ブログコンテンツ管理システム

このプロジェクトは、ブログコンテンツを統合的に管理するためのPythonベースのシステムです。現在は主にはてなブログからのコンテンツインポートに対応しています。

## 機能

- はてなブログからの記事インポート
- 記事のメタデータ管理
- タグ・カテゴリーの階層管理
- コンテンツのライフサイクル管理
- プラットフォーム固有の拡張機能
- メディア（画像）管理
- AIによる画像生成機能

## 必要条件

- Python 3.8以上
- 必要なパッケージ:
  ```
  pip install -r requirements.txt
  ```

## インストール

1. リポジトリをクローン:
   ```bash
   git clone https://github.com/yourusername/blog-content-manager.git
   cd blog-content-manager
   ```

2. 仮想環境を作成して有効化:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linuxの場合
   .\venv\Scripts\activate   # Windowsの場合
   ```

3. 依存パッケージをインストール:
   ```bash
   pip install -r requirements.txt
   ```

4. 環境変数の設定:
   - `.env.example`を`.env`にコピーして編集
   ```bash
   cp .env.example .env
   ```
   
   必要な環境変数:
   ```
   HATENA_ID=your_hatena_id
   BLOG_DOMAIN=your_blog_domain
   HATENA_BLOG_ATOMPUB_KEY=your_api_key
   ```

## 使用方法

### はてなブログからの記事インポート

```python
from blog_importer import BlogImporter, BlogImportConfig

# 設定を作成
config = BlogImportConfig(
    hatena_id="your_hatena_id",
    blog_domain="your_blog_domain",
    api_key="your_api_key"
)

# インポーターを初期化
importer = BlogImporter(config)

# 記事をインポート
result = importer.import_all_entries()

# 結果を処理
for entry in result["success"]:
    print(f"インポート成功: {entry.meta.title}")
```

### サンプルスクリプトの実行

```bash
python import_example.py
```

## プロジェクト構造

```
blog-content-manager/
├── blog_content.py      # 基本データモデル
├── blog_importer.py     # インポート機能
├── content_management.py # コンテンツ管理
├── media_management.py   # メディア管理
├── platform_extensions.py # プラットフォーム固有機能
├── import_example.py     # 使用例
└── requirements.txt      # 依存パッケージ
```

## データモデル

### BlogContent

メインのコンテンツモデルで、以下の情報を管理:

- 基本情報（ID、プラットフォーム、ステータスなど）
- メタデータ（タイトル、説明、タグなど）
- コンテンツ（本文、セクション）
- リンク（内部、外部、アフィリエイト）
- エンゲージメント（コメント、リアクション）
- アナリティクス（閲覧数、コンバージョンなど）
- ライフサイクル（更新頻度、レビュー日など）

### プラットフォーム拡張

各ブログプラットフォーム固有の機能をサポート:

- はてなブログ拡張
  - シンタックスハイライト
  - はてなブックマークボタン
  - 関連記事
  - 脚注

- Amebaブログ拡張
  - テーマカラー
  - カスタムヘッダー
  - 読了時間表示
  - いいねボタン

## 貢献

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 今後の予定

- [ ] WordPressサポートの追加
- [ ] メタディスクリプションの自動生成
- [ ] サムネイル画像の最適化
- [ ] SEO情報の自動抽出
- [ ] コンテンツの構造化解析
- [ ] 並行処理による高速化
- [ ] APIドキュメントの整備
- [ ] テストカバレッジの向上

## サポート

問題や質問がある場合は、GitHubのIssueを作成してください。 