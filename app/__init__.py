import os
from flask import Flask
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Instancias globales
oauth = OAuth()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'P1p3@_secret_key')

    # Configuración SMTP con SendGrid
    app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = 'apikey'  # Palabra literal requerida por SendGrid
    app.config['MAIL_PASSWORD'] = os.getenv('SENDGRID_API_KEY')
    
    sender_email = os.getenv('MAIL_DEFAULT_SENDER', 'b1cyruz@gmail.com')
    app.config['MAIL_DEFAULT_SENDER'] = ('EcoWatt', sender_email)

    # Inicializar extensiones
    mail.init_app(app)
    oauth.init_app(app)

    # Registrar cliente de Google OAuth
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Registrar rutas (Blueprint)
    from app.routes import main
    app.register_blueprint(main)

    return app