"""
要約機能の手動テスト用スクリプト
"""
import asyncio
import sys
import os
from pathlib import Path

# 適切なパスをインポートに追加
sys.path.append(str(Path(__file__).parent))

from line_webhook.app.summarizer import summarizer

async def run_test():
    """要約機能の基本的なテストを実行"""
    print("===== 要約機能テスト開始 =====")
    
    # テキスト要約のテスト
    print("\n----- テキスト要約テスト -----")
    short_text = "こんにちは、これはテストメッセージです。"
    long_text = "これは長いテキストメッセージのテストです。要約機能が正しく動作するかどうか確認します。" \
                "適切に先頭部分だけが抽出されるはずです。長すぎるテキストは省略されるはずです。" \
                "この部分は要約に含まれないはずです。"
    
    short_summary = await summarizer.summarize_text(short_text)
    print(f"短いテキスト要約: {short_summary}")
    
    long_summary = await summarizer.summarize_text(long_text)
    print(f"長いテキスト要約: {long_summary}")
    
    # 画像要約のテスト
    print("\n----- 画像要約テスト -----")
    try:
        image_path = Path("line_images/559134514040013260.jpg")
        if image_path.exists():
            image_summary = await summarizer.summarize_image(str(image_path))
            print(f"画像要約: {image_summary}")
        else:
            print(f"テスト用画像ファイルが見つかりません: {image_path}")
    except Exception as e:
        print(f"画像要約テスト中にエラー発生: {e}")
    
    # 完全な要約作成と保存のテスト
    print("\n----- 要約作成と保存テスト -----")
    test_user_id = "test_user_001"
    summary = await summarizer.create_summary(
        user_id=test_user_id,
        message_type="text",
        content="これは要約作成と保存のテスト用メッセージです。",
        filepath=None
    )
    print(f"作成された要約: {summary}")
    
    # 保存された要約の取得テスト
    print("\n----- 保存された要約の取得テスト -----")
    saved_summaries = await summarizer.get_recent_summaries(test_user_id)
    print(f"取得された要約（{len(saved_summaries)}件）:")
    for i, s in enumerate(saved_summaries, 1):
        print(f"{i}. {s.get('summary', 'No summary')} [{s.get('timestamp', 'No timestamp')}]")
    
    print("\n===== 要約機能テスト完了 =====")

# メインの実行部分
if __name__ == "__main__":
    asyncio.run(run_test())