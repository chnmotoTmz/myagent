from flask import Flask
from src.routes.api import api_bp

app = Flask(__name__)

# Register the API blueprint
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run()
