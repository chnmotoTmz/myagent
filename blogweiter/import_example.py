import os
from logger import log_debug
from blog_importer import BlogImporter, BlogImportConfig
from dotenv import load_dotenv

def main():
    # 環境変数を読み込み
    load_dotenv()
    
    # 設定を作成
    config = BlogImportConfig(
        hatena_id=os.getenv("HATENA_ID"),
        blog_domain=os.getenv("BLOG_DOMAIN"),
        api_key=os.getenv("HATENA_BLOG_ATOMPUB_KEY")
    )
    
    # インポーターを初期化
    importer = BlogImporter(config)
    
    try:
        # すべての記事をインポート
        result = importer.import_all_entries()
        
        # 成功した記事を処理
        for entry in result["success"]:
            print(f"インポート成功: {entry.meta.title}")
            print(f"  作成日時: {entry.created_at}")
            print(f"  カテゴリー: {entry.meta.category}")
            print(f"  タグ: {', '.join(entry.meta.tags)}")
            print("---")
        
        # エラーがあれば表示
        if result["errors"]:
            print("\nエラー:")
            for error in result["errors"]:
                print(f"- {error}")
        
        # 統計情報を表示
        print(f"\n合計記事数: {len(result['success'])}")
        print(f"エラー数: {len(result['errors'])}")
        
    except Exception as e:
        print(f"インポート処理中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
