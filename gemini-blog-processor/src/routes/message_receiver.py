from flask import Blueprint, request, jsonify
import os
import datetime
from datetime import timezone
import logging
from typing import Dict, Optional, Tuple

from src.database import db
from src.models import Message
from src.routes.line_webhook import BlogSeedManager

logger = logging.getLogger(__name__)

message_receiver_bp = Blueprint("message_receiver", __name__, url_prefix="/api")

ALLOWED_MESSAGE_TYPES = ["text", "image", "video"]


def save_message(data: Dict) -> Tuple[Optional[Message], Optional[str]]:
    try:
        content_to_save = data.get("content", "") if data["message_type"] == "text" else data.get("filepath", "")
        if not content_to_save and data["message_type"] != "text":
            logger.error(f"Missing filepath for media message_type: {data['message_type']}")
            return None, f"Missing filepath for {data['message_type']}"

        msg = Message(
            message_id=data["message_id"],
            user_id=data["user_id"],
            message_type=data["message_type"],
            content=content_to_save,
            timestamp=datetime.datetime.now(timezone.utc)
        )

        db.session.add(msg)
        db.session.commit()
        logger.info(f"Saved message (MVP - no duplicate check): {msg.message_id}")
        return msg, None

    except Exception as e:
        db.session.rollback()
        logger.error(f"DB error in save_message: {e}", exc_info=True)
        return None, f"Database error: {str(e)}"


def process_message_async(message: Message):
    try:
        logger.info(f"Processing message async (MVP): {message.message_id}")
        now = datetime.datetime.now(timezone.utc)
        minute = (now.minute // 5) * 5
        hour_key = f"{now.strftime('%Y%m%d%H')}{minute:02d}"

        manager = BlogSeedManager()
        processed_content = ""

        if message.message_type == "text":
            processed_content = f"""# Text Message (MVP)
\n## Received: {now.strftime('%Y-%m-%d %H:%M:%S')}
\n{message.content}"""
        elif message.message_type in ["image", "video"]:
            file_name = os.path.basename(message.content)
            processed_content = f"""# Media Message (MVP)
\n## Received: {now.strftime('%Y-%m-%d %H:%M:%S')}
\n- Type: {message.message_type}
\n- File: {file_name}
\n- Path: {message.content}"""
        else:
            logger.warning(f"Unsupported message type: {message.message_type} for message_id: {message.message_id}")
            return

        if processed_content:
            logger.info(f"Saving MVP blog seed for: {hour_key}")
            error = manager.save_seed(hour_key, processed_content)
            if error:
                logger.error(f"MVP seed save error: {error} for hour_key: {hour_key}")
            else:
                logger.info(f"MVP blog seed saved for: {hour_key}")
        else:
            logger.info(f"No content to save for message_id: {message.message_id}")

    except Exception as e:
        logger.error(f"Error in process_message_async (MVP) for {message.message_id}: {e}", exc_info=True)


@message_receiver_bp.route("/receive_message", methods=["POST"])
def receive_message():
    request_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{request_time_str}] /receive_message called (MVP)")

    if not request.is_json:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    try:
        data = request.get_json()

        required_fields = ["message_id", "user_id", "message_type"]
        if not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in data]
            return jsonify({"status": "error", "message": f"Missing essential fields: {', '.join(missing)}"}), 400

        if data["message_type"] == "text" and "content" not in data:
            return jsonify({"status": "error", "message": "Missing 'content' for text message"}), 400
        if data["message_type"] in ["image", "video"] and "filepath" not in data:
            return jsonify({"status": "error", "message": f"Missing 'filepath' for {data['message_type']} message"}), 400

        message_obj, error_msg = save_message(data)

        if error_msg:
            return jsonify({"status": "error", "message": error_msg}), 500

        if not message_obj:
            logger.error("save_message returned None without an error message, which is unexpected.")
            return jsonify({"status": "error", "message": "Failed to save message due to an unexpected issue"}), 500

        process_message_async(message_obj)

        return jsonify({
            "status": "success",
            "message": "Accepted (MVP)",
            "message_id": message_obj.message_id,
            "received_at": request_time_str
        }), 202

    except Exception as e:
        logger.error(f"Error in receive_message handler (MVP): {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Internal server error: {str(e)}"}), 500
