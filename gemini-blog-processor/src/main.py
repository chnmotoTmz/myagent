# /home/ubuntu/gemini_blog_processor/src/main.py
import os
import sys

# Add project root to Python path BEFORE other src imports
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 共通設定ファイルをインポート (.envファイルの読み込みはここで行われる)
from src.config import (
    DATABASE_URL, SECRET_KEY, PORT, DEBUG, LOG_LEVEL
)

import logging
from flask import Flask, send_from_directory, request, jsonify

# Import the db instance from the separated database module
from src.database import db # This should work now

# ロギング設定 - config.pyから設定値を取得
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
main_logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application."""
    main_logger.info("Creating Flask app instance.")
    # --- Database Configuration ---
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_path = os.path.join(basedir, "instance")
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
        main_logger.info(f"Created instance folder at: {instance_path}")

    app = Flask(__name__, 
                static_folder=os.path.join(os.path.dirname(__file__), "static"),
                instance_path=instance_path)
    
    # 共通設定ファイルから設定値を取得
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    main_logger.info(f"Database URI configured: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Initialize SQLAlchemy with the app
    db.init_app(app)
    main_logger.info("SQLAlchemy initialized with the app.")
    # --- End Database Configuration ---

    # Import models within the app context or ensure they are loaded
    # Importing them here ensures they are registered with SQLAlchemy
    with app.app_context():
        # Import models needed for db.create_all()
        # These imports should work now because sys.path was modified earlier
        from src.models import Message, BlogSeed, BlogIntentAnalysis
        main_logger.info("Models imported within app context.")

        # Import and register blueprints
        from src.routes.line_webhook import line_webhook_bp
        from src.routes.external_content import external_content_bp
        from src.routes.message_receiver import message_receiver_bp
        from src.routes.blog_intent import blog_intent_bp
        
        app.register_blueprint(line_webhook_bp)
        app.register_blueprint(external_content_bp)
        app.register_blueprint(message_receiver_bp)
        app.register_blueprint(blog_intent_bp)
        main_logger.info("Blueprints registered.")

    # --- Request Logging --- 
    @app.before_request
    def log_request_info():
        main_logger.debug(f"Request received: {request.method} {request.path}")
        main_logger.debug(f"Headers: {request.headers}")
        if request.data:
            try:
                main_logger.debug(f"Body: {request.get_json()}")
            except Exception:
                main_logger.debug(f"Body (raw): {request.get_data(as_text=True)}")

    @app.after_request
    def log_response_info(response):
        main_logger.debug(f"Response status: {response.status}")
        return response
    # --- End Request Logging ---

    # Serve static files - Modified to avoid catching API routes
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve(path):
        if path.startswith("api/"):
            pass # Let Flask handle routing for blueprints
            
        static_folder_path = app.static_folder
        if static_folder_path is None:
                return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        elif path == "" or path == "index.html":
            index_path = os.path.join(static_folder_path, "index.html")
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, "index.html")
            else:
                 return jsonify({"status": "running", "message": "API is active, no index.html found"}), 200
        else:
            return jsonify({"status": "error", "message": "Not Found"}), 404
            
    return app

app = create_app() # Create the app instance

if __name__ == "__main__":
    # 共通設定ファイルから設定値を取得
    main_logger.info(f"Starting Flask app on 0.0.0.0:{PORT} with debug={DEBUG}")
    # Create tables before running if they don't exist
    with app.app_context():
        # Models should be implicitly loaded via imports in create_app
        db.create_all() 
        main_logger.info("Ensured database tables exist.")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)

