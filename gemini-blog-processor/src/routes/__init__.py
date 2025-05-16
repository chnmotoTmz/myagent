# This file marks the directory as a Python package

# Import all blueprint objects
from src.routes.line_webhook import line_webhook_bp
from src.routes.message_receiver import message_receiver_bp
from src.routes.external_content import external_content_bp
from src.routes.user import user_bp
from src.routes.blog_intent import blog_intent_bp

# Export these blueprints to be registered in the application
__all__ = [
    'line_webhook_bp', 
    'message_receiver_bp', 
    'external_content_bp',
    'user_bp',
    'blog_intent_bp'
]
