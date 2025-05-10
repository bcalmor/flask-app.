from flask import Flask
from config import Config
from app.email import init_mail

def create_app():
    """Crear y configurar la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    init_mail(app)  # Inicializar Flask-Mail
    return app