"""
アプリケーション全体の設定を管理するモジュール
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple
import os
from pathlib import Path

@dataclass
class BrowserConfig:
    """ブラウザ設定"""
    debug_port: int = 9222
    timeout: int = 10
    headless: bool = False
    user_data_dir: Optional[str] = None

@dataclass
class DatabaseConfig:
    """データベース設定"""
    path: str = "ameba_posts.pkl"
    timeout: int = 5
    max_retries: int = 3

@dataclass
class GUIConfig:
    """GUI設定"""
    window_title: str = "Amebaブログ管理ツール"
    window_size: Tuple[int, int] = (1200, 800)
    min_window_size: Tuple[int, int] = (800, 600)
    refresh_interval: int = 60  # 記事一覧の自動更新間隔（秒）

@dataclass
class LogConfig:
    """ログ設定"""
    file_path: str = "ameba_automation.log"
    level: str = "INFO"
    format: str = '%(asctime)s - %(levelname)s - %(message)s'

@dataclass
class AppConfig:
    """アプリケーション全体の設定"""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)
    log: LogConfig = field(default_factory=LogConfig)

# デフォルト設定のインスタンスを作成
config = AppConfig()
