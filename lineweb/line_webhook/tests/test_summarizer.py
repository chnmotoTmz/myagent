"""
要約機能のテストモジュール
"""
import os
import pytest
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

from ..app.summarizer import MessageSummarizer

@pytest.fixture
def summarizer():
    """テスト用のMessageSummarizerインスタンスを作成"""
    # テスト用のストレージディレクトリを設定
    temp_dir = tempfile.mkdtemp()
    summarizer = MessageSummarizer()
    summarizer.summaries_dir = Path(temp_dir) / "summaries"
    summarizer.summaries_dir.mkdir(parents=True, exist_ok=True)
    return summarizer

@pytest.mark.asyncio
async def test_summarize_text_short(summarizer):
    """短いテキストの要約テスト"""
    short_text = "こんにちは、テスト中です。"
    result = await summarizer.summarize_text(short_text)
    assert "短いメッセージ:" in result
    assert short_text in result

@pytest.mark.asyncio
async def test_summarize_text_long(summarizer):
    """長いテキストの要約テスト"""
    long_text = "これは長いテキストメッセージのテストです。要約機能が正しく動作するかどうか確認します。" \
                "適切に先頭部分だけが抽出されるはずです。長すぎるテキストは省略されるはずです。" \
                "この部分は要約に含まれないはずです。"
    result = await summarizer.summarize_text(long_text)
    assert "長文メッセージ" in result
    assert "..." in result
    assert "先頭部分" in result
    assert "含まれないはずです" not in result

@pytest.mark.asyncio
async def test_summarize_image(summarizer):
    """画像ファイルの要約テスト"""
    # テスト用の画像ファイルを作成
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C')
        image_path = tmp.name
    
    try:
        result = await summarizer.summarize_image(image_path)
        assert "画像ファイル:" in result
        assert os.path.basename(image_path) in result
        assert "サイズ:" in result
        assert "KB" in result
    finally:
        # テストファイルを削除
        os.unlink(image_path)

@pytest.mark.asyncio
async def test_create_summary(summarizer):
    """要約作成の統合テスト"""
    test_user_id = "test_user_123"
    test_text = "テスト用のメッセージです。"
    
    summary = await summarizer.create_summary(
        user_id=test_user_id,
        message_type="text",
        content=test_text,
        filepath=None
    )
    
    # 返り値の検証
    assert summary["user_id"] == test_user_id
    assert summary["message_type"] == "text"
    assert "summary" in summary
    assert "テスト用のメッセージです" in summary["summary"]
    assert "timestamp" in summary
    
    # ファイルに保存されたか検証
    user_dir = summarizer.summaries_dir / test_user_id
    assert user_dir.exists()
    
    # 少なくとも1つのファイルがあるか確認
    files = list(user_dir.glob("summary_*.json"))
    assert len(files) > 0
    
    # ファイル内容を検証
    with open(files[0], "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    
    assert saved_data["user_id"] == test_user_id
    assert "テスト用のメッセージです" in saved_data["summary"]

@pytest.mark.asyncio
async def test_get_recent_summaries(summarizer):
    """最近の要約取得のテスト"""
    test_user_id = "test_user_456"
    
    # テスト用に複数の要約を作成
    for i in range(3):
        await summarizer.create_summary(
            user_id=test_user_id,
            message_type="text",
            content=f"テストメッセージ {i+1}",
            filepath=None
        )
    
    # 少し待って取得順序を確認しやすくする
    await asyncio.sleep(0.1)
    
    # 最新の要約を取得
    summaries = await summarizer.get_recent_summaries(test_user_id, limit=2)
    
    # 検証
    assert len(summaries) == 2  # 最新の2つだけ取得されるはず
    assert summaries[0]["summary"].endswith("3")  # 最新のものが最初にあるはず
    assert summaries[1]["summary"].endswith("2")  # 2番目に新しいもの