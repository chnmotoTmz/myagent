# /home/ubuntu/gemini_blog_processor/src/routes/external_content.py

from flask import Blueprint, request, jsonify, current_app
import os
import datetime
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

external_content_bp = Blueprint("external_content", __name__, url_prefix="/api/v1")

# --- Simple API Key Authentication --- 
# In a real app, store keys securely, not hardcoded!
VALID_API_KEYS = {
    "your_secret_key_1": "client_A",
    "your_secret_key_2": "client_B"
    # Add more keys as needed
}

# Placeholder for storing received external content (replace with database)
received_external_content = []

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key in VALID_API_KEYS:
            # Optionally, you can log which client accessed
            logger.info(f"API Key validated for client: {VALID_API_KEYS[api_key]}")
            return f(*args, **kwargs)
        else:
            logger.warning(f"Invalid or missing API Key: {api_key}")
            return jsonify({"status": "error", "message": "Unauthorized - Invalid or missing API Key"}), 401
    return decorated_function

@external_content_bp.route("/external-content", methods=["POST"])
@require_api_key
def handle_external_content():
    """Handles incoming content from external sources."""
    if not request.is_json:
        logger.warning("External content request is not JSON")
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    data = request.get_json()
    logger.info(f"Received external content data: {data}")

    # --- Input Validation (Based on pasted_content_2.txt) ---
    required_fields = ["source_type", "content_id", "body"]
    if not all(field in data for field in required_fields):
        missing = [field for field in required_fields if field not in data]
        logger.warning(f"Missing required fields in external content: {missing}")
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing)}"}), 400

    # --- Store Received Content (In-memory example) ---
    # You might want to process this data similarly to LINE messages or store it differently
    content_data = {
        "source_type": data["source_type"],
        "content_id": data["content_id"],
        "title": data.get("title"),
        "body": data["body"],
        "published_at": data.get("published_at"),
        "author_name": data.get("author_name"),
        "tags": data.get("tags", []),
        "metadata": data.get("metadata", {}),
        "received_at": datetime.datetime.now()
    }
    received_external_content.append(content_data)
    logger.info(f"Stored external content {data['content_id']} from source {data['source_type']}")

    # --- TODO: Add processing logic for external content --- 
    # Should this also trigger Gemini processing? Or be stored for later use?
    # For now, just acknowledge receipt.

    return jsonify({
        "status": "success",
        "message": "Data received successfully.",
        "received_content_id": data["content_id"]
    }), 202 # Accepted, assuming processing happens later

