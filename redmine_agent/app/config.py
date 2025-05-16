"""
Redmineチケット管理エージェント - 設定モジュール

設定の管理と永続化を担当するモジュール
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# 共通ロガー設定
logger = logging.getLogger(__name__)

class Config:
    """設定管理クラス"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス (Noneの場合はデフォルト位置)
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # デフォルトは data/config.json
            self.config_path = Path(__file__).parent.parent / "data" / "config.json"
          # 初期設定
        self.config = {
            "llm": {
                "enabled": True,
                "model": "gemini-2.0-flash",
                "temperature": 0.7,
                "use_local_fallback": True,
            },
            "notification": {
                "morning_report_enabled": True,
                "evening_report_enabled": True,
                "morning_report_time": "09:00",
                "evening_report_time": "18:00",
            },
            "system": {
                "environment": "development",
                "debug_mode": True,
                "version": "1.0.0"
            },
            "user_preferences": {}
        }
        
        # 設定ファイルの読み込み
        self._load_config()
    
    def _load_config(self) -> None:
        """設定ファイルの読み込み"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    # 既存設定にマージ（深いマージはせず、トップレベルのみ）
                    for key, value in loaded_config.items():
                        self.config[key] = value
                logger.info(f"設定を読み込みました: {self.config_path}")
            else:
                # 設定ファイルが存在しない場合はデフォルトを保存
                self._save_config()
                logger.info(f"デフォルト設定を作成しました: {self.config_path}")
        except Exception as e:
            logger.error(f"設定ファイルの読み込み中にエラー: {str(e)}")
    
    def _save_config(self) -> None:
        """設定ファイルの保存"""
        try:
            # 親ディレクトリが存在することを確認
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"設定を保存しました: {self.config_path}")
        except Exception as e:
            logger.error(f"設定ファイルの保存中にエラー: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値の取得
        
        Args:
            key: 設定キー（ドット区切りで階層指定可）
            default: デフォルト値
            
        Returns:
            設定値またはデフォルト値
        """
        try:
            parts = key.split(".")
            value = self.config
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        設定値の設定
        
        Args:
            key: 設定キー（ドット区切りで階層指定可）
            value: 設定値
        """
        try:
            parts = key.split(".")
            target = self.config
            
            # 最後の部分以外をたどる
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            
            # 値を設定
            target[parts[-1]] = value
            
            # 変更を保存
            self._save_config()
            
        except Exception as e:
            logger.error(f"設定の更新中にエラー: {str(e)}")
    
    def update_user_preference(self, user_id: str, key: str, value: Any) -> None:
        """
        ユーザー設定の更新
        
        Args:
            user_id: ユーザーID
            key: 設定キー
            value: 設定値
        """
        if "user_preferences" not in self.config:
            self.config["user_preferences"] = {}
            
        if user_id not in self.config["user_preferences"]:
            self.config["user_preferences"][user_id] = {}
            
        self.config["user_preferences"][user_id][key] = value
        self._save_config()
    
    def get_user_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """
        ユーザー設定の取得
        
        Args:
            user_id: ユーザーID
            key: 設定キー
            default: デフォルト値
            
        Returns:
            設定値またはデフォルト値
        """
        try:
            return self.config["user_preferences"][user_id][key]
        except (KeyError, TypeError):
            return default


# シングルトンインスタンスの作成
config = Config()

# 外部からimportして使う
get_config = config.get
set_config = config.set
update_user_preference = config.update_user_preference
get_user_preference = config.get_user_preference
