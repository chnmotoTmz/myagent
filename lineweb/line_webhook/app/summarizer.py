"""
LINE メッセージ内容を要約するためのユーティリティモジュール
"""
import os
import logging
from datetime import datetime
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import STORAGE_PATH from main or a central config
from .main import STORAGE_PATH # Assuming STORAGE_PATH is accessible from main

# ロギングの設定
logger = logging.getLogger(__name__)

class MessageSummarizer:
    def __init__(self):
        """初期化"""
        self.summaries_dir = Path(STORAGE_PATH) / 'summaries'
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

    def _setup_logging(self):
        """要約処理専用のロギング設定"""
        log_file = Path('logs/summarizer.log')
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)

    async def summarize_text(self, text: str) -> str:
        """テキストメッセージを要約"""
        try:
            # テキストの長さに基づいて要約方法を変える
            if len(text) <= 50:
                return f"短いメッセージ: {text}"
            else:
                # 簡易的な要約（実際の実装ではもっと高度な手法を使用する）
                words = text.split()
                first_part = ' '.join(words[:10])
                return f"長文メッセージ（先頭部分）: {first_part}..."
        except Exception as e:
            logger.error(f"テキスト要約中にエラー発生: {e}")
            return "テキスト要約に失敗しました"

    async def summarize_image(self, image_path: str) -> str:
        """画像を要約
        
        注: 実際のプロダクションコードでは、Google Vision APIや
        他の画像分析サービスを使用することをお勧めします
        """
        try:
            # 画像ファイルの基本情報を取得
            file_stats = os.stat(image_path)
            file_size_kb = file_stats.st_size / 1024
            file_name = os.path.basename(image_path)
            
            # 時刻情報を抽出（ファイル名から）
            timestamp = file_name.split('_')[0]
            time_str = f"{timestamp[:4]}年{timestamp[4:6]}月{timestamp[6:8]}日{timestamp[8:10]}時{timestamp[10:12]}分"
            
            # Google Vision APIが利用可能な場合は画像分析を行う
            if os.getenv('GOOGLE_API_KEY'):
                # TODO: Google Vision APIを使用した画像分析
                # ここでは基本情報のみ
                summary = f"画像メッセージ（{time_str}に受信）\nファイル: {file_name}\nサイズ: {file_size_kb:.1f}KB"
            else:
                summary = f"画像メッセージ（{time_str}に受信）\nファイル: {file_name}\nサイズ: {file_size_kb:.1f}KB"
            
            return summary
            
        except Exception as e:
            logger.error(f"画像要約中にエラー発生: {e}")
            return "画像要約に失敗しました"

    async def summarize_video(self, video_path: str) -> str:
        """動画を要約"""
        try:
            # 動画ファイルの基本情報を取得
            file_stats = os.stat(video_path)
            file_size_mb = file_stats.st_size / (1024 * 1024)
            file_name = os.path.basename(video_path)
            
            # 時刻情報を抽出（ファイル名から）
            timestamp = file_name.split('_')[0]
            time_str = f"{timestamp[:4]}年{timestamp[4:6]}月{timestamp[6:8]}日{timestamp[8:10]}時{timestamp[10:12]}分"
            
            # 実際の環境では動画分析APIを使用して以下の情報も取得可能：
            # - 動画の長さ
            # - 解像度
            # - 主要なシーンの説明
            # など
            
            summary = f"動画メッセージ（{time_str}に受信）\nファイル: {file_name}\nサイズ: {file_size_mb:.1f}MB"
            return summary
            
        except Exception as e:
            logger.error(f"動画要約中にエラー発生: {e}")
            return "動画要約に失敗しました"

    async def create_summary(self, user_id: str, message_type: str, content: Any, 
                           filepath: Optional[str] = None) -> Dict[str, Any]:
        """メッセージタイプに応じた要約を生成"""
        try:
            summary_text = ""
            if message_type == "text":
                summary_text = await self.summarize_text(content)
            elif message_type == "image":
                if filepath:
                    summary_text = await self.summarize_image(filepath)
                else:
                    summary_text = "画像ファイルパスがありません"
            elif message_type == "video":
                if filepath:
                    summary_text = await self.summarize_video(filepath)
                else:
                    summary_text = "動画ファイルパスがありません"
            else:
                summary_text = f"未サポートのメッセージタイプ: {message_type}"
            
            summary = {
                "user_id": user_id,
                "message_type": message_type,
                "summary": summary_text,
                "timestamp": datetime.now().isoformat(),
                "filepath": filepath
            }
            
            # ユーザーごとに要約を保存
            await self.save_summary(user_id, summary)
            return summary
            
        except Exception as e:
            logger.error(f"要約作成中にエラー発生: {e}", exc_info=True)
            return {
                "user_id": user_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def save_summary(self, user_id: str, summary: Dict[str, Any]) -> bool:
        """ユーザー別に要約を保存"""
        try:
            # ユーザー別のディレクトリを作成（親ディレクトリも含めて作成）
            user_dir = self.summaries_dir / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # 日付を使ってファイル名を生成
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            summary_file = user_dir / f"summary_{timestamp}.json"
            
            # 要約をJSONとして保存（非同期I/O）
            json_str = json.dumps(summary, ensure_ascii=False, indent=2)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: summary_file.write_text(json_str, encoding='utf-8')
            )
            
            logger.info(f"要約を保存しました: {summary_file}")
            return True
            
        except Exception as e:
            logger.error(f"要約保存中にエラー発生 (ユーザー {user_id}): {e}", exc_info=True)
            return False

    async def get_recent_summaries(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """特定ユーザーの最近の要約を取得"""
        try:
            # ユーザーのディレクトリを確認
            user_dir = self.summaries_dir / user_id
            if not user_dir.exists():
                return []
                
            # すべての要約ファイルを取得して新しい順にソート
            summary_files = list(user_dir.glob("summary_*.json"))
            summary_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # 最新のものから指定数だけ取得
            recent_files = summary_files[:limit]
            
            summaries = []
            for file_path in recent_files:
                try:
                    loop = asyncio.get_running_loop()
                    content = await loop.run_in_executor(None, file_path.read_text)
                    summary = json.loads(content)
                    summaries.append(summary)
                except Exception as e:
                    logger.error(f"要約ファイル {file_path} の読み込みエラー: {e}")
                    
            return summaries
            
        except Exception as e:
            logger.error(f"最近の要約取得中にエラー発生 (ユーザー {user_id}): {e}", exc_info=True)
            return []

# グローバルインスタンス
summarizer = MessageSummarizer()