from flask import Flask
from config import Config

def create_app():
    """Crea y configura una instancia de la aplicación Flask."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # El 'with' asegura que el contexto de la aplicación esté disponible
    with app.app_context():
        # Importar e inicializar el módulo de la base de datos
        from . import db
        db.init_app(app)

        # Importar las rutas después de inicializar la BD
        from . import routes

    return app
