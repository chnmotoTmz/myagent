"""
Redmineチケット管理エージェント - ロギングユーティリティ

ロギングの設定と、エンコーディングの問題を解決するためのユーティリティ機能を提供します。
"""

import logging
import sys
from typing import Optional

class UnicodeStreamHandler(logging.StreamHandler):
    """
    Unicode文字をサポートするカスタムStreamHandler
    
    Windows上のコンソールでUnicode文字（特に絵文字や特殊文字）を
    安全に表示するためのハンドラです。
    """
    
    def __init__(self, stream=None):
        """
        ハンドラの初期化
        
        Args:
            stream: 出力先ストリーム (デフォルトはsys.stderr)
        """
        super().__init__(stream)
        self.encoding = "utf-8"
        
    def emit(self, record):
        """
        ログレコードを出力
        
        Args:
            record: ログレコード
        """
        try:
            msg = self.format(record)
            stream = self.stream
            # Windows console (cp932) can't display some Unicode characters
            try:
                # Try to encode with console's encoding
                if hasattr(stream, 'encoding') and stream.encoding:
                    msg.encode(stream.encoding)
            except UnicodeEncodeError:
                # If it fails, replace unsupported characters with '?'
                if hasattr(stream, 'encoding') and stream.encoding:
                    msg = msg.encode(stream.encoding, errors='replace').decode(stream.encoding)
            
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(log_file: Optional[str] = None, level: int = logging.INFO):
    """
    アプリケーションのロギングを設定
    
    Args:
        log_file: ログファイルのパス (Noneの場合はファイル出力なし)
        level: ログレベル (デフォルトはINFO)
    """
    handlers = []
    
    # ファイルハンドラ
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        handlers.append(file_handler)
    
    # コンソールハンドラ（Unicode対応）
    console_handler = UnicodeStreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        '%Y-%m-%d %H:%M:%S'
    ))
    handlers.append(console_handler)
    
    # ロギング設定
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True  # 既存の設定を上書き
    )
