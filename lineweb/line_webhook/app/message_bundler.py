import os
import json
from datetime import datetime
import logging
from typing import Dict, List, Optional

# Import STORAGE_PATH from config
from .config import STORAGE_PATH

logger = logging.getLogger(__name__)

class MessageBundle:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages: List[Dict] = []
        self.last_update = datetime.now()

    def add_message(self, message_data: Dict):
        self.messages.append(message_data)
        self.last_update = datetime.now()

def process_new_message(user_id: str, file_path: str) -> bool:
    """
    新しいメッセージをバンドルに追加し、必要に応じて処理します。
    """
    try:
        # ファイルの内容を読み込み
        message_data = _read_message_file(file_path)
        if not message_data:
            return False

        # バンドルを更新
        bundle = _get_or_create_bundle(user_id)
        bundle.add_message(message_data)

        # バンドルを保存
        _save_bundle(bundle)

        return True

    except Exception as e:
        logger.error(f"Error processing message for user {user_id}: {e}", exc_info=True)
        return False

def _read_message_file(file_path: str) -> Optional[Dict]:
    """メッセージファイルの内容を読み込みます"""
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return {
                    'type': 'text',
                    'content': content,
                    'filepath': file_path,
                    'timestamp': datetime.now().isoformat()
                }
        else:
            # 画像やビデオファイルの場合はファイルパスのみを記録
            return {
                'type': 'media',
                'filepath': file_path,
                'timestamp': datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error reading message file {file_path}: {e}", exc_info=True)
        return None

def _get_bundle_path(user_id: str) -> str:
    """ユーザーのバンドルファイルパスを取得"""
    bundle_dir = os.path.join(STORAGE_PATH, 'bundles')
    os.makedirs(bundle_dir, exist_ok=True)
    return os.path.join(bundle_dir, f"{user_id}_bundle.json")

def _get_or_create_bundle(user_id: str) -> MessageBundle:
    """既存のバンドルを読み込むか、新しいバンドルを作成"""
    bundle_path = _get_bundle_path(user_id)
    bundle = MessageBundle(user_id)

    if os.path.exists(bundle_path):
        try:
            with open(bundle_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                bundle.messages = data.get('messages', [])
                if 'last_update' in data:
                    bundle.last_update = datetime.fromisoformat(data['last_update'])
        except Exception as e:
            logger.error(f"Error loading bundle for user {user_id}: {e}", exc_info=True)

    return bundle

def _save_bundle(bundle: MessageBundle):
    """バンドルをJSONファイルとして保存"""
    try:
        bundle_path = _get_bundle_path(bundle.user_id)
        data = {
            'user_id': bundle.user_id,
            'messages': bundle.messages,
            'last_update': bundle.last_update.isoformat()
        }
        with open(bundle_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved bundle for user {bundle.user_id}")
    except Exception as e:
        logger.error(f"Error saving bundle for user {bundle.user_id}: {e}", exc_info=True)