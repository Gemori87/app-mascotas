import mysql.connector
from flask import current_app, g

def get_db():
    """
    Función para obtener una conexión a la base de datos.
    Reutiliza la conexión si ya existe en el contexto de la petición (g).
    """
    if 'db' not in g:
        try:
            config = current_app.config
            g.db = mysql.connector.connect(
                host=config['DB_HOST'],
                user=config['DB_USER'],
                password=config['DB_PASSWORD'],
                database=config['DB_DATABASE']
            )
        except mysql.connector.Error as err:
            print(f"Error al conectar a la base de datos: {err}")
            g.db = None 
    return g.db

def close_db(e=None):
    """
    Cierra la conexión a la base de datos al final de la petición.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    """
    Registra la función de cierre de la base de datos con la aplicación Flask.
    """
    app.teardown_appcontext(close_db)
