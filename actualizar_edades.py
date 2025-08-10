#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar las edades de todas las mascotas
"""

from app import create_app
from app.db import get_db
from datetime import datetime
import mysql.connector

def actualizar_edades_mascotas():
    """
    Actualiza la edad de todas las mascotas basándose en su fecha de nacimiento
    """
    conn = get_db()
    if not conn:
        print("Error: No se pudo conectar a la base de datos")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener todas las mascotas con fecha de nacimiento
        cursor.execute("SELECT Idmascota, fecha_nac FROM mascota WHERE fecha_nac IS NOT NULL")
        mascotas = cursor.fetchall()
        
        actualizadas = 0
        
        for mascota in mascotas:
            if mascota['fecha_nac']:
                # Calcular edad
                fecha_nacimiento = mascota['fecha_nac']
                fecha_actual = datetime.now().date()
                
                # Si fecha_nac es datetime, convertir a date
                if isinstance(fecha_nacimiento, datetime):
                    fecha_nacimiento = fecha_nacimiento.date()
                
                # Calcular diferencia en años
                edad = fecha_actual.year - fecha_nacimiento.year
                
                # Ajustar si no ha cumplido años este año
                if (fecha_actual.month, fecha_actual.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
                    edad -= 1
                
                # Asegurar que la edad no sea negativa
                edad = max(0, edad)
                
                # Actualizar en la base de datos
                cursor.execute(
                    "UPDATE mascota SET edad = %s WHERE Idmascota = %s",
                    (edad, mascota['Idmascota'])
                )
                actualizadas += 1
                print(f"Mascota ID {mascota['Idmascota']}: edad actualizada a {edad} años")
        
        conn.commit()
        print(f"✅ Se actualizaron {actualizadas} mascotas exitosamente")
        
    except mysql.connector.Error as err:
        print(f"❌ Error al actualizar edades: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        actualizar_edades_mascotas()
