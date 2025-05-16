# ブログコンテンツ管理システム API仕様書

## 概要
このAPIは、はてなブログやアメブロからRSSフィードを介して記事を取得し、管理するための機能を提供します。

## RSSReader クラス

### 初期化
```python
reader = RSSReader()
```

#### 設定されるフィード
- はてなブログ:
  - https://motochan1969.hatenablog.com/rss
  - https://lifehacking1919.hatenablog.jp/rss
  - https://arafo40tozan.hatenadiary.jp/rss
- アメブロ:
  - http://rssblog.ameba.jp/motochan1969/rss.html

### メソッド

#### get_entries()
全てのフィードから記事を取得します。

**戻り値**: `List[Dict[str, Any]]`
```python
[
    {
        'title': str,          # 記事タイトル
        'link': str,           # 記事URL
        'content': str,        # 記事本文（HTMLタグ除去済み）
        'created_at': datetime, # 作成日時（UTC）
        'updated_at': datetime, # 更新日時（UTC）
        'category': str,       # カテゴリー
        'tags': List[str],     # タグリスト
        'platform': str,       # プラットフォーム（'hatena' or 'ameblo'）
        'source_feed': str     # フィードURL
    },
    ...
]
```

#### get_feed_stats()
フィードの統計情報を取得します。

**戻り値**: `Dict[str, int]`
```python
{
    'total_entries': int,     # 全記事数
    'hatena_entries': int,    # はてなブログの記事数
    'ameblo_entries': int     # アメブロの記事数
}
```

### 内部メソッド

#### _parse_date(date_str: str) -> datetime
日付文字列をパースしてdatetimeオブジェクトを返します。
- タイムゾーン情報がない場合はUTCとして扱います
- パースに失敗した場合は現在時刻（UTC）を返します

#### _clean_html(html_content: str) -> str
HTMLコンテンツからタグを除去し、プレーンテキストを返します。
- スクリプトとスタイルタグを削除
- 連続する空白を1つに統合
- 前後の空白を除去

#### _extract_tags(entry: Dict[str, Any]) -> List[str]
記事エントリーからタグリストを抽出します。
- 空のタグは除外されます
- タグが存在しない場合は空リストを返します

#### _extract_category(entry: Dict[str, Any]) -> str
記事エントリーからカテゴリーを抽出します。
- カテゴリーが存在しない場合は最初のタグを使用
- どちらも存在しない場合は 'uncategorized' を返します

#### _fetch_feed(feed_url: str) -> Dict
指定されたURLからフィードを取得します。
- User-Agentヘッダーを設定
- タイムアウト: 10秒
- SSL証明書の検証を無効化（開発環境用）
- エンコーディングを自動検出

## エラーハンドリング

### 日付パースエラー
- 無効な日付形式の場合は現在時刻（UTC）を使用
- タイムゾーン情報がない場合はUTCとして扱う

### ネットワークエラー
- 接続タイムアウト: 10秒後にエラー
- SSL証明書エラー: 検証をスキップ
- その他のHTTPエラー: エラーメッセージを出力し空の結果を返す

### コンテンツエラー
- 無効なHTML: BeautifulSoupでクリーニング
- 文字エンコーディング: 自動検出して適切に処理
- フィードフォーマットエラー: 警告を出力して続行

## 使用例

```python
# RSSリーダーの初期化
reader = RSSReader()

# 全記事の取得
entries = reader.get_entries()

# 統計情報の取得
stats = reader.get_feed_stats()

# 記事の処理
for entry in entries:
    print(f"タイトル: {entry['title']}")
    print(f"作成日時: {entry['created_at']}")
    print(f"カテゴリー: {entry['category']}")
    print(f"タグ: {', '.join(entry['tags'])}")
    print(f"プラットフォーム: {entry['platform']}")
    print("---")
```

## 注意事項

1. **SSL証明書**
   - 開発環境では証明書検証を無効化しています
   - 本番環境では適切な証明書検証を行うべきです

2. **タイムゾーン**
   - 全ての日時はUTCで統一されています
   - 表示時に必要に応じてローカルタイムに変換してください

3. **パフォーマンス**
   - フィード取得は同期的に行われます
   - 多数のフィードを扱う場合は非同期処理の実装を検討してください

4. **エラー処理**
   - 個々の記事の処理エラーは記録されますが、処理は継続されます
   - フィード全体の取得エラーは空のリストを返します 