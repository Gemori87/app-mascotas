from flask import Flask
from config import Config
from flask_mail import Mail, Message

mail = Mail()

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
     # Configuración de Flask-Mail (ejemplo con Gmail)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'barricar90@gmail.com'      
    app.config['MAIL_PASSWORD'] = 'paan xxxo hdbw gpuo'
    app.config['MAIL_DEFAULT_SENDER'] = ('MediPet', 'barricar90@gmail.com')

    mail.init_app(app)
    
    # Agregar funciones al contexto de las plantillas
    from datetime import datetime
    
    @app.context_processor
    def inject_now():
        return {'now': datetime.now}
    
    return app
