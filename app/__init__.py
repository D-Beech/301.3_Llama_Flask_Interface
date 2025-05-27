from flask import Flask
from flask_cors import CORS
from .routes.chat import chat_bp
from .routes.docx import docx_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Register Blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(docx_bp)

    return app
