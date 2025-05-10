import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_secret_key'
    JSON_DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
    
    # Configuración de Flask-Mail
    MAIL_SERVER = 'smtp.gmail.com'  # Cambia esto según tu proveedor de correo
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'becalmor@gmail.com'  # Email directamente en el código (temporal)
    MAIL_PASSWORD = 'ruxq usmh tibb jgrg'  # Contraseña de aplicación directamente en el código (temporal)
    MAIL_DEFAULT_SENDER = 'becalmor@gmail.com'  # Email desde el que se enviarán los correos
