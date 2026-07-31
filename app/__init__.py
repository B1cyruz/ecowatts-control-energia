import os
from flask import Flask
from authlib.integrations.flask_client import OAuth

# 1. Instanciamos OAuth a nivel global para poder exportarlo
oauth = OAuth()

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