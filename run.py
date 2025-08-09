from app import create_app, mail
from app.db import get_db
from flask_mail import Message
from flask import render_template
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import mysql.connector

app = create_app()

def enviar_recordatorios_citas():
    """Busca citas para mañana y envía un recordatorio por correo."""
    with app.app_context(): 
        print("Ejecutando tarea de recordatorios...")
        
        conn = get_db()
        if not conn:
            print("Error de conexión en el scheduler.")
            return

        cursor = conn.cursor(dictionary=True)
        
        # Calcula la fecha de mañana
        tomorrow = datetime.now().date() + timedelta(days=1)
        
        try:
            # Busca citas programadas para mañana
            query = """
                SELECT c.idmascota, c.fecha, c.motivo
                FROM cita c
                WHERE DATE(c.fecha) = %s AND c.estado = 1
            """
            cursor.execute(query, (tomorrow,))
            citas_para_manana = cursor.fetchall()
            
            print(f"Se encontraron {len(citas_para_manana)} citas para mañana.")

            for cita in citas_para_manana:
                
                from app.routes import enviar_correo_cita
                enviar_correo_cita(
                    cita['idmascota'],
                    cita['fecha'],
                    cita['motivo'],
                    "Recordatorio de Cita en MediPet para Mañana"
                )
                print(f"Recordatorio enviado para la cita de la mascota {cita['idmascota']}.")

        except mysql.connector.Error as err:
            print(f"Error en scheduler al buscar citas: {err}")
        finally:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    # Configuración del Scheduler
    scheduler = BackgroundScheduler(daemon=True)
    # Programa la tarea para que se ejecute todos los días a las 07:00 AM
    scheduler.add_job(enviar_recordatorios_citas, 'cron', hour=7, minute=0)
    scheduler.start()

    print("Scheduler iniciado. La aplicación está lista.")
    
    app.run(debug=True, use_reloader=False)