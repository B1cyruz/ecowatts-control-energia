import os
from flask import Flask
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth

# 1. Instanciamos OAuth a nivel global para poder exportarlo
oauth = OAuth()
mail = Mail()

def create_app():
    app = Flask(__name__)
    
    # Configuración SMTP (Ejemplo con Gmail)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'tu_correo_emisor@gmail.com'  # O variable de entorno
    app.config['MAIL_PASSWORD'] = 'tu_contraseña_de_aplicacion' # Clave de aplicación de Google
    app.config['MAIL_DEFAULT_SENDER'] = ('EcoWatt', 'tu_correo_emisor@gmail.com')
    app.config['SECRET_KEY'] = 'tu_llave_secreta_super_segura'   # Necesaria para firmar tokens

    mail.init_app(app)
    return app

def create_app():
    app = Flask(__name__)
    app.secret_key = 'P1p3@'

    # 2. Inicializamos oauth con la app
    oauth.init_app(app)

    # 3. Registramos el cliente de Google usando las variables del .env 
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Importamos y registramos las rutas
    from app.routes import main
    app.register_blueprint(main)

    return app