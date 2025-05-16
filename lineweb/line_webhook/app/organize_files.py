import os
import shutil
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def organize_files_by_type(source_dir: str) -> dict:
    """
    指定されたディレクトリ内のファイルを種類別に整理します
    """
    if not os.path.exists(source_dir):
        logger.error(f"Source directory does not exist: {source_dir}")
        return {"error": "Directory not found"}

    # 整理結果を追跡
    organization_result = {
        "images": [],
        "videos": [],
        "texts": [],
        "others": []
    }

    try:
        # 年月のサブディレクトリを作成
        current_date = datetime.now()
        year_month = current_date.strftime("%Y_%m")
        type_dirs = {
            "images": os.path.join(source_dir, year_month, "images"),
            "videos": os.path.join(source_dir, year_month, "videos"),
            "texts": os.path.join(source_dir, year_month, "texts"),
            "others": os.path.join(source_dir, year_month, "others")
        }

        # 必要なディレクトリを作成
        for dir_path in type_dirs.values():
            os.makedirs(dir_path, exist_ok=True)

        # ファイルを種類別に振り分け
        for filename in os.listdir(source_dir):
            if filename.startswith('.'): # 隠しファイルをスキップ
                continue

            file_path = os.path.join(source_dir, filename)
            if not os.path.isfile(file_path): # ディレクトリをスキップ
                continue

            # ファイルの種類を判断
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                dest_dir = type_dirs["images"]
                organization_result["images"].append(filename)
            elif filename.lower().endswith(('.mp4', '.mov', '.avi')):
                dest_dir = type_dirs["videos"]
                organization_result["videos"].append(filename)
            elif filename.lower().endswith(('.txt', '.md')):
                dest_dir = type_dirs["texts"]
                organization_result["texts"].append(filename)
            else:
                dest_dir = type_dirs["others"]
                organization_result["others"].append(filename)

            # ファイルを移動
            dest_path = os.path.join(dest_dir, filename)
            shutil.move(file_path, dest_path)
            logger.info(f"Moved {filename} to {dest_path}")

        return organization_result

    except Exception as e:
        logger.error(f"Error organizing files in {source_dir}: {e}", exc_info=True)
        return {"error": str(e)}