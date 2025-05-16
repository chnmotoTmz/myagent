# /home/ubuntu/gemini_blog_processor/src/models/__init__.py

# Import models to make them easily accessible from the package
from src.models.message import Message
from src.models.user import User
from src.models.blog_seed import BlogSeed
from src.models.blog_intent import BlogIntentAnalysis

# You might also want to define __all__ if you prefer explicit exports
__all__ = ['Message', 'User', 'BlogSeed', 'BlogIntentAnalysis']

