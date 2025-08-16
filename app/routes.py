from flask import render_template, request, redirect, url_for, flash, session, current_app, make_response
from datetime import datetime, timedelta, date
import mysql.connector
import secrets
from .db import get_db
from flask_mail import Message
from app import mail
import re
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.pdfgen import canvas

app = current_app

def render_personas_with_preserved_data():
    """Función auxiliar para renderizar gestion_personas.html preservando los datos del formulario"""
    conn = get_db()
    personas = []
    if conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT Idpersona, nom1, apell1, correo, cedula, estado
                FROM Persona
                ORDER BY Idpersona DESC
            """)
            personas = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error al obtener personas: {err}")
            personas = []
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    # Pasar los datos del formulario directamente al template
    form_data = {
        'nom1': request.form.get('nom1', ''),
        'nom2': request.form.get('nom2', ''),
        'apell1': request.form.get('apell1', ''),
        'apell2': request.form.get('apell2', ''),
        'cedula': request.form.get('cedula', ''),
        'correo': request.form.get('correo', ''),
        'direccion': request.form.get('direccion', ''),
        'tele': request.form.get('tele', ''),
        'movil': request.form.get('movil', ''),
        'fecha_nac': request.form.get('fecha_nac', '')
    }
    
    return render_template('gestion_personas.html', personas=personas, form_data=form_data, preserve_data=True)


@app.route('/persona/crear', methods=['POST'])
def crear_persona():
    nom1   = request.form['nom1'].strip()
    apell1 = request.form['apell1'].strip()
    correo = request.form['correo'].strip()
    cedula = request.form['cedula'].strip()

    # Validaciones básicas
    if not nom1 or not apell1 or not correo or not cedula:
        flash('Primer nombre, primer apellido, correo y cédula son obligatorios.', 'error')
        return render_personas_with_preserved_data()

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return render_personas_with_preserved_data()

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # 1) Verificar si ya existen administradores
        cursor.execute("""
            SELECT COUNT(u.Idusuario) AS admin_count
            FROM Usuario u
            JOIN Perfil  p ON u.idperfil = p.Idperfil
            WHERE p.descripc = 'Administrador'
        """)
        has_admins = cursor.fetchone()['admin_count'] > 0

        # 2) Pre-chequeo de duplicados (correo y cedula)
        cursor.execute("SELECT 1 FROM Persona WHERE correo = %s", (correo,))
        if cursor.fetchone():
            flash('El correo electrónico ya está registrado.', 'error')
            return render_personas_with_preserved_data()

        cursor.execute("SELECT 1 FROM Persona WHERE cedula = %s", (cedula,))
        if cursor.fetchone():
            flash('La cédula ya está registrada.', 'error')
            return render_personas_with_preserved_data()

        # 3) Insert
        query = """
            INSERT INTO Persona
              (nom1, nom2, apell1, apell2, direccion, tele, movil, correo, cedula, fecha_nac)
            VALUES
              (%s,   %s,   %s,     %s,     %s,        %s,   %s,    %s,     %s,     %s)
        """
        fecha_nac = request.form.get('fecha_nac') or None
        cursor.execute(query, (
            nom1, request.form.get('nom2'),
            apell1, request.form.get('apell2'),
            request.form.get('direccion'),
            request.form.get('tele'),
            request.form.get('movil'),
            correo, cedula, fecha_nac
        ))

        new_persona_id = cursor.lastrowid
        conn.commit()

        # 4) Redirección según haya admins o no
        if not has_admins:
            return redirect(url_for('crear_primer_admin', persona_id=new_persona_id))
        else:
            flash('Persona registrada exitosamente. Un administrador debe crear su cuenta de usuario para poder ingresar al sistema.', 'success')
            return redirect(url_for('gestion_personas'))

    except mysql.connector.Error as err:
        if conn:
            try:
                conn.rollback()
            except:
                pass

        if err.errno == 1062:
            # Mensaje más específico según la clave única que saltó
            em = str(err).lower()
            if 'correo' in em:
                flash('Error: El correo ya está registrado.', 'error')
            elif 'cedula' in em:
                flash('Error: La cédula ya está registrada.', 'error')
            else:
                flash('Error: registro duplicado.', 'error')
        else:
            flash(f'Error al crear la persona: {err}', 'error')
        return render_personas_with_preserved_data()
    except Exception as ex:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        flash(f'Error inesperado: {ex}', 'error')
        return render_personas_with_preserved_data()
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

@app.route('/crear-primer-admin/<int:persona_id>', methods=['GET', 'POST'])
def crear_primer_admin(persona_id):
    if request.method == 'POST':
        nombreu = request.form['nombreu']
        contrasena = request.form['contrasena']
        if not nombreu or not contrasena:
            flash('El nombre de usuario y la contraseña son obligatorios.', 'error')
            return redirect(url_for('crear_primer_admin', persona_id=persona_id))

        conn = get_db()
        if not conn:
            flash('Error de conexión.', 'error')
            return redirect(url_for('crear_primer_admin', persona_id=persona_id))
        
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Buscamos el ID del perfil 'Administrador'
            cursor.execute("SELECT Idperfil FROM Perfil WHERE descripc = 'Administrador'")
            admin_perfil = cursor.fetchone()
            if not admin_perfil:
                flash('Error crítico: El perfil "Administrador" no existe en la base de datos.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('login'))

            # Creamos el usuario
            query = "INSERT INTO Usuario (nombreu, contrasena, idpersona, idperfil) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nombreu, contrasena, persona_id, admin_perfil['Idperfil']))
            conn.commit()

            cursor.close()
            conn.close()
            flash('¡Cuenta de Administrador creada exitosamente! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            conn.rollback()
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            if err.errno == 1062:
                flash('Error: Ese nombre de usuario ya está en uso. Por favor, elige otro.', 'error')
            else:
                flash(f'Error al crear la cuenta de administrador: {err}', 'error')
            return redirect(url_for('crear_primer_admin', persona_id=persona_id))

    
    return render_template('crear_primer_admin.html', persona_id=persona_id)



@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nombreu = request.form['usuario']
        contrasena = request.form['contrasena']
        if not nombreu or not contrasena:
            flash('Usuario y contraseña son requeridos.', 'error')
            return redirect(url_for('login'))

        conn = get_db()
        if not conn:
            flash('Error de conexión con la base de datos.', 'error')
            return redirect(url_for('login'))
        
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            # Primero busca si existe el usuario
            cursor.execute("SELECT * FROM Usuario WHERE nombreu = %s", (nombreu,))
            user = cursor.fetchone()
            
            if not user:
                flash('El usuario no se encuentra registrado.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('login'))
            
            # Si existe, revisa contraseña y estado
            if user['contrasena'] != contrasena:
                flash('Contraseña incorrecta.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('login'))
                
            if not user['estado']:
                flash('El usuario está inactivo.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('login'))
            
            # Si todo OK, busca perfil y loguea
            cursor.execute("SELECT descripc FROM Perfil WHERE Idperfil = %s", (user['idperfil'],))
            perfil = cursor.fetchone()
            
            # Configurar sesión
            session.clear()
            session['user_id'] = user['Idusuario']
            session['user_name'] = user['nombreu']
            session['user_profile'] = perfil['descripc'] if perfil else ''
            
            cursor.close()
            conn.close()
            return redirect(url_for('menu_principal'))
            
        except mysql.connector.Error as err:
            flash(f'Error de base de datos: {err}', 'error')
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error inesperado: {e}', 'error')
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            return redirect(url_for('login'))
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))

@app.route('/menu')
def menu_principal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('menu.html')

@app.route('/personas', methods=['GET', 'POST'])
def gestion_personas():
    conn = get_db()
    personas = []
    if conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT Idpersona, nom1, apell1, correo, cedula, estado
                FROM Persona
                ORDER BY Idpersona DESC
            """)
            personas = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error al obtener personas: {err}")
            flash('Error al cargar la lista de personas', 'error')
            personas = []
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass
    return render_template('gestion_personas.html', personas=personas)

@app.route('/persona/editar/<int:id>', methods=['GET', 'POST'])
def editar_persona(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_personas'))

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            # chequear duplicado de correo (otra persona con mismo correo)
            correo = request.form['correo']
            cursor.execute("SELECT 1 FROM Persona WHERE correo = %s AND Idpersona <> %s", (correo, id))
            if cursor.fetchone():
                flash('El correo electrónico ya está registrado en otra persona.', 'error')
                return redirect(url_for('editar_persona', id=id))

            # chequear duplicado de cedula (otra persona con misma cedula)
            cedula = request.form['cedula']
            cursor.execute("SELECT 1 FROM Persona WHERE cedula = %s AND Idpersona <> %s", (cedula, id))
            if cursor.fetchone():
                flash('La cédula ya está registrada en otra persona.', 'error')
                return redirect(url_for('editar_persona', id=id))

            update_query = """
                UPDATE Persona
                   SET nom1=%s, nom2=%s, apell1=%s, apell2=%s,
                       direccion=%s, tele=%s, movil=%s, correo=%s,
                       cedula=%s, fecha_nac=%s
                 WHERE Idpersona=%s
            """
            fecha_nac = request.form.get('fecha_nac') or None
            cursor.execute(update_query, (
                request.form['nom1'], request.form.get('nom2'),
                request.form['apell1'], request.form.get('apell2'),
                request.form.get('direccion'), request.form.get('tele'),
                request.form.get('movil'), request.form['correo'],
                request.form['cedula'], fecha_nac, id
            ))
            conn.commit()
            flash('Persona actualizada correctamente.', 'success')
            return redirect(url_for('gestion_personas'))

        # GET - Obtener datos de la persona
        cursor.execute("SELECT * FROM Persona WHERE Idpersona = %s", (id,))
        persona = cursor.fetchone()

        if persona:
            return render_template('editar_persona.html', persona=persona)
        else:
            flash('Persona no encontrada.', 'error')
            return redirect(url_for('gestion_personas'))

    except mysql.connector.Error as err:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        if err.errno == 1062:
            em = str(err).lower()
            if 'correo' in em:
                flash('Error: El correo ya está registrado.', 'error')
            elif 'cedula' in em:
                flash('Error: La cédula ya está registrada.', 'error')
            else:
                flash('Error: registro duplicado.', 'error')
        else:
            flash(f'Error al actualizar la persona: {err}', 'error')
        return redirect(url_for('gestion_personas'))
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        flash(f'Error inesperado: {e}', 'error')
        return redirect(url_for('gestion_personas'))
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

@app.route('/persona/inhabilitar/<int:id>')
def inhabilitar_persona(id):
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        # Verifica si tiene usuario activo
        cursor.execute("SELECT Idusuario FROM Usuario WHERE idpersona = %s AND estado = TRUE", (id,))
        if cursor.fetchone():
            flash('No se puede inhabilitar una persona con un usuario activo.', 'error')
        else:
            try:
                # Consulta estado actual
                cursor.execute("SELECT estado FROM Persona WHERE Idpersona = %s", (id,))
                row = cursor.fetchone()
                if row is not None:
                    nuevo_estado = not bool(row['estado'])
                    cursor.execute("UPDATE Persona SET estado = %s WHERE Idpersona = %s", (nuevo_estado, id))
                    conn.commit()
                    flash('Estado de la persona cambiado correctamente.', 'success')
                else:
                    flash('Persona no encontrada.', 'error')
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f'Error al cambiar el estado: {err}', 'error')
    return redirect(url_for('gestion_personas'))



@app.route('/perfiles')
def gestion_perfiles():
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))
    conn = get_db()
    perfiles = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Idperfil, descripc, estado FROM Perfil ORDER BY Idperfil DESC")
        perfiles = cursor.fetchall()
    return render_template('gestion_perfiles.html', perfiles=perfiles)

@app.route('/perfil/crear', methods=['POST'])
def crear_perfil():
    if session.get('user_profile') != 'Administrador': return redirect(url_for('login'))
    conn = get_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Perfil (descripc) VALUES (%s)", (request.form['descripc'],))
            conn.commit()
            flash('Perfil creado exitosamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al crear el perfil: {err}', 'error')
    return redirect(url_for('gestion_perfiles'))

@app.route('/perfil/editar/<int:id>', methods=['GET', 'POST'])
def editar_perfil(id):
    if session.get('user_profile') != 'Administrador': return redirect(url_for('login'))
    conn = get_db()
    if not conn:
        flash('Error de conexión.', 'error')
        return redirect(url_for('gestion_perfiles'))
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        try:
            descripc = request.form['descripc']
            cursor.execute("UPDATE Perfil SET descripc = %s WHERE Idperfil = %s", (descripc, id))
            conn.commit()
            flash('Perfil actualizado correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al actualizar el perfil: {err}', 'error')
        return redirect(url_for('gestion_perfiles'))
    cursor.execute("SELECT * FROM Perfil WHERE Idperfil = %s", (id,))
    perfil = cursor.fetchone()
    if perfil:
        return render_template('editar_perfil.html', perfil=perfil)
    else:
        flash('Perfil no encontrado.', 'error')
        return redirect(url_for('gestion_perfiles'))

@app.route('/perfil/inhabilitar/<int:id>')
def inhabilitar_perfil(id):
    if session.get('user_profile') != 'Administrador': return redirect(url_for('login'))
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total FROM Usuario WHERE idperfil = %s AND estado = TRUE", (id,))
        if cursor.fetchone()['total'] > 0:
            flash('No se puede inhabilitar un perfil con usuarios activos asociados.', 'error')
        else:
            try:
                cursor.execute("UPDATE Perfil SET estado = NOT estado WHERE Idperfil = %s", (id,))
                conn.commit()
                flash('Estado del perfil cambiado correctamente.', 'success')
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f'Error al cambiar el estado del perfil: {err}', 'error')
    return redirect(url_for('gestion_perfiles'))

@app.route('/medicamentos', methods=['GET', 'POST'])
def gestion_medicamentos():
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))
    
    if request.method == 'POST':
        # Procesar creación de medicamento
        nombre = request.form.get('nombre', '').strip()
        presentacion = request.form.get('presentacion', '').strip()
        
        if not nombre or not presentacion:
            flash('Nombre y presentación son obligatorios.', 'error')
            return redirect(url_for('gestion_medicamentos'))
        
        conn = get_db()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                
                # Verificar si ya existe un medicamento con el mismo nombre y presentación
                cursor.execute("""
                    SELECT 1 FROM medicamento 
                    WHERE nombre = %s AND presentacion = %s
                """, (nombre, presentacion))
                
                if cursor.fetchone():
                    flash('Ya existe un medicamento con el mismo nombre y presentación.', 'error')
                    cursor.close()
                    conn.close()
                    return redirect(url_for('gestion_medicamentos'))
                
                # Insertar nuevo medicamento
                cursor.execute("""
                    INSERT INTO medicamento (nombre, presentacion, estado)
                    VALUES (%s, %s, 1)
                """, (nombre, presentacion))
                
                conn.commit()
                cursor.close()
                conn.close()
                flash('Medicamento creado exitosamente.', 'success')
                
            except mysql.connector.Error as err:
                if conn: conn.rollback()
                flash(f'Error al crear el medicamento: {err}', 'error')
                if cursor: cursor.close()
                if conn: conn.close()
        
        return redirect(url_for('gestion_medicamentos'))
    
    # Método GET - Mostrar lista de medicamentos
    conn = get_db()
    medicamentos = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT Idmedicamento, nombre, presentacion, estado
            FROM medicamento
            ORDER BY Idmedicamento DESC
        """)
        medicamentos = cursor.fetchall()
        cursor.close()
        conn.close()
    
    return render_template('gestion_medicamentos.html', medicamentos=medicamentos)

@app.route('/medicamento/editar/<int:id>', methods=['GET', 'POST'])
def editar_medicamento(id):
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_medicamentos'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        presentacion = request.form.get('presentacion', '').strip()
        
        if not nombre or not presentacion:
            flash('Nombre y presentación son obligatorios.', 'error')
            return redirect(url_for('editar_medicamento', id=id))
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Verificar si ya existe otro medicamento con el mismo nombre y presentación
            cursor.execute("""
                SELECT 1 FROM medicamento 
                WHERE nombre = %s AND presentacion = %s AND Idmedicamento != %s
            """, (nombre, presentacion, id))
            
            if cursor.fetchone():
                flash('Ya existe otro medicamento con el mismo nombre y presentación.', 'error')
                cursor.close()
                conn.close()
                return redirect(url_for('editar_medicamento', id=id))
            
            # Actualizar medicamento
            cursor.execute("""
                UPDATE medicamento 
                SET nombre = %s, presentacion = %s
                WHERE Idmedicamento = %s
            """, (nombre, presentacion, id))
            
            conn.commit()
            cursor.close()
            conn.close()
            flash('Medicamento actualizado exitosamente.', 'success')
            return redirect(url_for('gestion_medicamentos'))
            
        except mysql.connector.Error as err:
            if conn: conn.rollback()
            flash(f'Error al actualizar el medicamento: {err}', 'error')
            if cursor: cursor.close()
            if conn: conn.close()
            return redirect(url_for('editar_medicamento', id=id))
    
    # Método GET - Mostrar formulario de edición
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT Idmedicamento, nombre, presentacion, estado
            FROM medicamento
            WHERE Idmedicamento = %s
        """, (id,))
        medicamento = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not medicamento:
            flash('Medicamento no encontrado.', 'error')
            return redirect(url_for('gestion_medicamentos'))
        
        return render_template('editar_medicamento.html', medicamento=medicamento)
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar el medicamento: {err}', 'error')
        if cursor: cursor.close()
        if conn: conn.close()
        return redirect(url_for('gestion_medicamentos'))

@app.route('/medicamento/inhabilitar/<int:id>')
def inhabilitar_medicamento(id):
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_medicamentos'))

    try:
        cursor = conn.cursor(dictionary=True)
        
        # Obtener el estado actual del medicamento
        cursor.execute("""
            SELECT estado, nombre FROM medicamento WHERE Idmedicamento = %s
        """, (id,))
        medicamento = cursor.fetchone()
        
        if not medicamento:
            flash('Medicamento no encontrado.', 'error')
            cursor.close()
            conn.close()
            return redirect(url_for('gestion_medicamentos'))
        
        # Cambiar el estado
        nuevo_estado = 0 if medicamento['estado'] else 1
        accion = "habilitado" if nuevo_estado else "deshabilitado"
        
        cursor.execute("""
            UPDATE medicamento 
            SET estado = %s
            WHERE Idmedicamento = %s
        """, (nuevo_estado, id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash(f'Medicamento "{medicamento["nombre"]}" {accion} exitosamente.', 'success')
        
    except mysql.connector.Error as err:
        if conn: conn.rollback()
        flash(f'Error al cambiar el estado del medicamento: {err}', 'error')
        if cursor: cursor.close()
        if conn: conn.close()
    
    return redirect(url_for('gestion_medicamentos'))

@app.route('/veterinarios')
def gestion_veterinarios():
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))

    conn = get_db()
    usuarios, personas, perfiles, mascotas, asignaciones = [], [], [], [], []

    if conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)

            # Usuarios veterinarios ya registrados (solo perfil veterinario idperfil = 6)
            query_usuarios = """
                SELECT u.Idusuario, u.nombreu, CONCAT(pe.nom1, ' ', pe.apell1) as nombre_persona,
                       pe.nom1, pe.apell1, pr.descripc, u.estado
                FROM Usuario u
                JOIN Persona pe ON u.idpersona = pe.Idpersona
                JOIN Perfil pr ON u.idperfil = pr.Idperfil
                WHERE u.estado = 1 AND u.idperfil = 6
                ORDER BY pe.nom1, pe.apell1
            """
            cursor.execute(query_usuarios)
            usuarios = cursor.fetchall()

            # Personas sin usuario asignado (para crear nuevos usuarios)
            cursor.execute("""
                SELECT Idpersona, CONCAT(nom1, ' ', apell1) as nombre_completo
                FROM Persona
                WHERE estado = TRUE AND Idpersona NOT IN (SELECT idpersona FROM Usuario WHERE estado = 1)
            """)
            personas = cursor.fetchall()

            # Perfiles activos
            cursor.execute("SELECT Idperfil, descripc FROM Perfil WHERE estado = TRUE")
            perfiles = cursor.fetchall()

            # Mascotas activas (solo las que no tienen veterinario asignado)
            cursor.execute("""
                SELECT m.Idmascota, m.nombre, m.codigo,
                       CONCAT(p.nom1, ' ', p.apell1) as nombre_dueno
                FROM mascota m
                JOIN persona p ON m.idduenio = p.Idpersona
                WHERE m.estado = 1
                ORDER BY m.nombre
            """)
            mascotas = cursor.fetchall()

            # Obtener las asignaciones actuales (mascotas asignadas a veterinarios)
            cursor.execute("""
                SELECT m.Idmascota, m.nombre as nombre_mascota, m.codigo,
                       u.Idusuario, u.nombreu, 
                       CONCAT(p.nom1, ' ', p.apell1) as nombre_persona,
                       CONCAT(due.nom1, ' ', due.apell1) as nombre_dueno
                FROM mascota m
                JOIN Usuario u ON m.idveterinario = u.Idusuario
                JOIN Persona p ON u.idpersona = p.Idpersona
                JOIN persona due ON m.idduenio = due.Idpersona
                WHERE m.idveterinario IS NOT NULL AND m.estado = 1 AND u.estado = 1 AND u.idperfil = 6
                ORDER BY m.nombre
            """)
            asignaciones = cursor.fetchall()

        except mysql.connector.Error as err:
            flash(f'Error al cargar los datos: {err}', 'error')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template(
        'gestion_veterinarios.html',
        usuarios=usuarios,
        personas=personas,
        perfiles=perfiles,
        mascotas=mascotas,
        asignaciones=asignaciones
    )


@app.route('/usuarios')
def gestion_usuarios():
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))
    conn = get_db()
    usuarios, personas, perfiles = [], [], []
    if conn:
        cursor = conn.cursor(dictionary=True)
        query_usuarios = "SELECT u.Idusuario, u.nombreu, CONCAT(pe.nom1, ' ', pe.apell1) as nombre_persona, pr.descripc, u.estado FROM Usuario u JOIN Persona pe ON u.idpersona = pe.Idpersona JOIN Perfil pr ON u.idperfil = pr.Idperfil ORDER BY u.Idusuario DESC"
        cursor.execute(query_usuarios)
        usuarios = cursor.fetchall()
        cursor.execute("SELECT Idpersona, CONCAT(nom1, ' ', apell1) as nombre_completo FROM Persona WHERE estado = TRUE AND Idpersona NOT IN (SELECT idpersona FROM Usuario)")
        personas = cursor.fetchall()
        cursor.execute("SELECT Idperfil, descripc FROM Perfil WHERE estado = TRUE")
        perfiles = cursor.fetchall()
    return render_template('gestion_usuarios.html', usuarios=usuarios, personas=personas, perfiles=perfiles)

@app.route('/usuario/crear', methods=['POST'])
def crear_usuario():
    if session.get('user_profile') != 'Administrador':
        return redirect(url_for('login'))
    conn = get_db()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO Usuario (nombreu, contrasena, idpersona, idperfil) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (
                request.form['nombreu'],
                request.form['contrasena'],
                request.form['idpersona'],
                request.form['idperfil']
            ))
            conn.commit()
            # Obtener correo electrónico de la persona
            cursor.execute("SELECT correo FROM Persona WHERE Idpersona = %s", (request.form['idpersona'],))
            persona = cursor.fetchone()
            correo = persona[0] if persona else None
            # Enviar el correo solo si hay dirección
            if correo:
                enviar_correo_credenciales(
                    correo, 
                    request.form['nombreu'], 
                    request.form['contrasena']
                )
            flash('Usuario creado exitosamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            if err.errno == 1062:
                flash('Error: El nombre de usuario o la persona ya están en uso.', 'error')
            else:
                flash(f'Error al crear el usuario: {err}', 'error')
    return redirect(url_for('gestion_usuarios'))

# Función auxiliar para enviar correo
def enviar_correo_credenciales(correo_destino, usuario, contrasena):
    from app import mail
    msg = Message('Tus credenciales de acceso',
                  sender='tu_correo@gmail.com',
                  recipients=[correo_destino])
    msg.body = f"""
    Hola, tu usuario ha sido creado en el sistema MediPet.

    Usuario: {usuario}
    Contraseña: {contrasena}

    Por favor, ingresa y cambia tu contraseña después de iniciar sesión.
    """
    mail.send(msg)

@app.route('/usuario/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    if session.get('user_profile') != 'Administrador': return redirect(url_for('login'))
    conn = get_db()
    if not conn:
        flash('Error de conexión.', 'error')
        return redirect(url_for('gestion_usuarios'))
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        try:
            nombreu = request.form['nombreu']
            contrasena = request.form['contrasena']
            idperfil = request.form['idperfil']
            if contrasena:
                query = "UPDATE Usuario SET nombreu = %s, contrasena = %s, idperfil = %s WHERE Idusuario = %s"
                cursor.execute(query, (nombreu, contrasena, idperfil, id))
            else:
                query = "UPDATE Usuario SET nombreu = %s, idperfil = %s WHERE Idusuario = %s"
                cursor.execute(query, (nombreu, idperfil, id))
            conn.commit()
            flash('Usuario actualizado correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al actualizar el usuario: {err}', 'error')
        return redirect(url_for('gestion_usuarios'))
    query_usuario = "SELECT u.*, CONCAT(p.nom1, ' ', p.apell1) as nombre_persona FROM Usuario u JOIN Persona p ON u.idpersona = p.Idpersona WHERE u.Idusuario = %s"
    cursor.execute(query_usuario, (id,))
    usuario = cursor.fetchone()
    cursor.execute("SELECT Idperfil, descripc FROM Perfil WHERE estado = TRUE")
    perfiles = cursor.fetchall()
    if usuario:
        return render_template('editar_usuario.html', usuario=usuario, perfiles=perfiles)
    else:
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('gestion_usuarios'))

@app.route('/usuario/inhabilitar/<int:id>')
def inhabilitar_usuario(id):
    if session.get('user_profile') != 'Administrador': return redirect(url_for('login'))
    conn = get_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE Usuario SET estado = NOT estado WHERE Idusuario = %s", (id,))
            conn.commit()
            flash('Estado del usuario cambiado correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al cambiar el estado del usuario: {err}', 'error')
    return redirect(url_for('gestion_usuarios'))


# ... otras rutas ...

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        correo = request.form['correo']
        conn = get_db()
        # <-- El truco va aquí: buffered=True
        cursor_select = conn.cursor(dictionary=True, buffered=True)
        cursor_select.execute(
            "SELECT Idusuario FROM Usuario u JOIN Persona p ON u.idpersona = p.Idpersona WHERE p.correo = %s",
            (correo,))
        user = cursor_select.fetchone()
        cursor_select.close()

        if user:
            token = secrets.token_urlsafe(32)
            expires = datetime.datetime.now() + datetime.timedelta(hours=1)

            cursor_insert = conn.cursor()
            cursor_insert.execute(
                "INSERT INTO reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)",
                (user['Idusuario'], token, expires)
            )
            conn.commit()
            cursor_insert.close()

            reset_url = url_for('reset_password', token=token, _external=True)
            send_email(
                correo,
                "Restablecer contraseña - MediPet",
                f"""
                <p>Hola,</p>
                <p>Haz clic en el siguiente enlace para restablecer tu contraseña:</p>
                <p><a href="{reset_url}">{reset_url}</a></p>
                <p>Este enlace expirará en 1 hora.</p>
                """
            )
            flash('Se envió un correo con instrucciones para restablecer tu contraseña.', 'info')
        else:
            flash('Si el correo existe, recibirás instrucciones para restablecer tu contraseña.', 'info')
        return redirect(url_for('login'))
    return render_template('olvido_contra.html')

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Aquí va el formulario y la lógica para cambiar la contraseña usando el token
    # Ejemplo mínimo:
    if request.method == 'POST':
        nueva = request.form['contrasena']
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT user_id, expires_at FROM reset_tokens WHERE token = %s", (token,))
        token_row = cursor.fetchone()
        import datetime
        if not token_row or datetime.datetime.now() > token_row['expires_at']:
            flash('El enlace de restablecimiento es inválido o ha expirado.', 'error')
            return redirect(url_for('login'))
        user_id = token_row['user_id']
        cursor.execute("UPDATE Usuario SET contrasena = %s WHERE Idusuario = %s", (nueva, user_id))
        cursor.execute("DELETE FROM reset_tokens WHERE token = %s", (token,))
        conn.commit()
        flash('Contraseña actualizada exitosamente. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

def send_email(to, subject, html_body):
    msg = Message(
        subject,
        recipients=[to],
        html=html_body,
        charset='utf-8'   # <<--- LA LÍNEA CLAVE
    )
    mail.send(msg)


# ==================== GESTIÓN DE PROCEDIMIENTOS ====================

@app.route('/procedimientos')
def gestion_procedimientos():
    """Gestión de tipos de procedimientos"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('menu_principal'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM tipoprocedimiento ORDER BY nombre")
        procedimientos = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Error al consultar procedimientos: {err}', 'error')
        procedimientos = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('gestion_procedimientos.html', procedimientos=procedimientos)


@app.route('/procedimiento/crear', methods=['POST'])
def crear_procedimiento():
    """Crear un nuevo tipo de procedimiento"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    nombre = request.form.get('nombre', '').strip()
    
    if not nombre:
        flash('El nombre del procedimiento es obligatorio.', 'error')
        return redirect(url_for('gestion_procedimientos'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_procedimientos'))
    
    cursor = conn.cursor()
    
    try:
        # Verificar si ya existe un procedimiento con el mismo nombre
        cursor.execute("SELECT Idprocedimiento FROM tipoprocedimiento WHERE nombre = %s", (nombre,))
        if cursor.fetchone():
            flash('Ya existe un procedimiento con ese nombre.', 'error')
            return redirect(url_for('gestion_procedimientos'))
        
        # Crear el procedimiento
        query = "INSERT INTO tipoprocedimiento (nombre, estado) VALUES (%s, 1)"
        cursor.execute(query, (nombre,))
        conn.commit()
        
        flash('Procedimiento creado exitosamente.', 'success')
        
    except mysql.connector.Error as err:
        flash(f'Error al crear procedimiento: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('gestion_procedimientos'))


@app.route('/procedimiento/editar/<int:id>', methods=['GET', 'POST'])
def editar_procedimiento(id):
    """Editar un tipo de procedimiento existente"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_procedimientos'))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        
        if not nombre:
            flash('El nombre del procedimiento es obligatorio.', 'error')
            return redirect(url_for('editar_procedimiento', id=id))
        
        try:
            # Verificar si ya existe otro procedimiento con el mismo nombre
            cursor.execute("SELECT Idprocedimiento FROM tipoprocedimiento WHERE nombre = %s AND Idprocedimiento != %s", (nombre, id))
            if cursor.fetchone():
                flash('Ya existe otro procedimiento con ese nombre.', 'error')
                return redirect(url_for('editar_procedimiento', id=id))
            
            # Actualizar el procedimiento
            query = "UPDATE tipoprocedimiento SET nombre = %s WHERE Idprocedimiento = %s"
            cursor.execute(query, (nombre, id))
            conn.commit()
            
            flash('Procedimiento actualizado exitosamente.', 'success')
            return redirect(url_for('gestion_procedimientos'))
            
        except mysql.connector.Error as err:
            flash(f'Error al actualizar procedimiento: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    # GET: Obtener datos del procedimiento
    try:
        cursor.execute("SELECT * FROM tipoprocedimiento WHERE Idprocedimiento = %s", (id,))
        procedimiento = cursor.fetchone()
        
        if not procedimiento:
            flash('Procedimiento no encontrado.', 'error')
            return redirect(url_for('gestion_procedimientos'))
            
    except mysql.connector.Error as err:
        flash(f'Error al buscar procedimiento: {err}', 'error')
        return redirect(url_for('gestion_procedimientos'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('editar_procedimiento.html', procedimiento=procedimiento)


@app.route('/procedimiento/inhabilitar/<int:id>')
def inhabilitar_procedimiento(id):
    """Habilitar/deshabilitar tipo de procedimiento"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Solo administradores pueden inhabilitar
    if session.get('user_profile') != 'Administrador':
        flash('No tiene permisos para realizar esta acción.', 'error')
        return redirect(url_for('gestion_procedimientos'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_procedimientos'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener estado actual
        cursor.execute("SELECT estado FROM tipoprocedimiento WHERE Idprocedimiento = %s", (id,))
        procedimiento = cursor.fetchone()
        
        if not procedimiento:
            flash('Procedimiento no encontrado.', 'error')
            return redirect(url_for('gestion_procedimientos'))
        
        # Cambiar estado
        nuevo_estado = 0 if procedimiento['estado'] else 1
        cursor.execute("UPDATE tipoprocedimiento SET estado = %s WHERE Idprocedimiento = %s", (nuevo_estado, id))
        conn.commit()
        
        accion = 'habilitado' if nuevo_estado else 'deshabilitado'
        flash(f'Procedimiento {accion} exitosamente.', 'success')
        
    except mysql.connector.Error as err:
        flash(f'Error al cambiar estado de procedimiento: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('gestion_procedimientos'))


@app.route('/procedimiento/ver/<int:id>')
def ver_procedimiento(id):
    """Ver detalles de un tipo de procedimiento específico"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_procedimientos'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM tipoprocedimiento WHERE Idprocedimiento = %s", (id,))
        procedimiento = cursor.fetchone()
        
        if not procedimiento:
            flash('Procedimiento no encontrado.', 'error')
            return redirect(url_for('gestion_procedimientos'))
            
    except mysql.connector.Error as err:
        flash(f'Error al buscar procedimiento: {err}', 'error')
        return redirect(url_for('gestion_procedimientos'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('ver_procedimiento.html', procedimiento=procedimiento)


# ==================== GESTIÓN DE PROCEDIMIENTOS DE MASCOTAS ====================

@app.route('/procedimientos-mascotas')
def gestion_procedimientos_mascotas():
    """Visualizar lista de procedimientos aplicados a mascotas"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    procedimientos_mascotas = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                pm.Idregistro,
                m.nombre as nombre_mascota,
                tp.nombre as nombre_procedimiento,
                pm.fecha,
                pm.observacion,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_veterinario,
                pm.estado
            FROM procedimientomascota pm
            JOIN mascota m ON pm.idmascota = m.Idmascota
            JOIN tipoprocedimiento tp ON pm.idprocedimiento = tp.Idprocedimiento
            LEFT JOIN persona p ON pm.idveterinario = p.Idpersona
            ORDER BY pm.fecha DESC, pm.Idregistro DESC
        """)
        procedimientos_mascotas = cursor.fetchall()
    return render_template('gestion_procedimientos_mascotas.html', procedimientos_mascotas=procedimientos_mascotas)


@app.route('/procedimiento-mascota/crear', methods=['GET', 'POST'])
def crear_procedimiento_mascota():
    """Crear un nuevo registro de procedimiento para mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_procedimientos_mascotas'))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        idmascota = request.form['idmascota']
        idprocedimiento = request.form['idprocedimiento']
        fecha = request.form['fecha']
        observacion = request.form.get('observacion', '')
        idveterinario = request.form.get('idveterinario') or None
        
        if not idmascota or not idprocedimiento or not fecha:
            flash('La mascota, procedimiento y fecha son obligatorios.', 'error')
            return redirect(url_for('crear_procedimiento_mascota'))

        try:
            query = """
                INSERT INTO procedimientomascota (idmascota, idprocedimiento, fecha, observacion, idveterinario, estado)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (idmascota, idprocedimiento, fecha, observacion, idveterinario, True))
            conn.commit()
            flash('Procedimiento registrado exitosamente.', 'success')
            return redirect(url_for('gestion_procedimientos_mascotas'))
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al registrar el procedimiento: {err}', 'error')
            return redirect(url_for('crear_procedimiento_mascota'))
    
    # GET: Cargar datos para formulario
    try:
        # Obtener mascotas activas
        cursor.execute("SELECT Idmascota, nombre FROM mascota WHERE estado = TRUE ORDER BY nombre")
        mascotas = cursor.fetchall()
        
        # Obtener tipos de procedimientos activos
        cursor.execute("SELECT Idprocedimiento, nombre FROM tipoprocedimiento WHERE estado = TRUE ORDER BY nombre")
        tipos_procedimientos = cursor.fetchall()
        
        # Obtener veterinarios (personas que pueden ser veterinarios)
        cursor.execute("""
            SELECT Idpersona, CONCAT(nom1, ' ', apell1) as nombre_completo 
            FROM persona 
            WHERE estado = TRUE 
            ORDER BY nom1, apell1
        """)
        veterinarios = cursor.fetchall()
        
        return render_template('crear_procedimiento_mascota.html', 
                             mascotas=mascotas, 
                             tipos_procedimientos=tipos_procedimientos, 
                             veterinarios=veterinarios)
    except mysql.connector.Error as err:
        flash(f'Error al cargar los datos: {err}', 'error')
        return redirect(url_for('gestion_procedimientos_mascotas'))


@app.route('/procedimiento-mascota/editar/<int:id>', methods=['GET', 'POST'])
def editar_procedimiento_mascota(id):
    """Editar un registro de procedimiento de mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_procedimientos_mascotas'))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        idmascota = request.form['idmascota']
        idprocedimiento = request.form['idprocedimiento']
        fecha = request.form['fecha']
        observacion = request.form.get('observacion', '')
        idveterinario = request.form.get('idveterinario') or None
        
        if not idmascota or not idprocedimiento or not fecha:
            flash('La mascota, procedimiento y fecha son obligatorios.', 'error')
            return redirect(url_for('editar_procedimiento_mascota', id=id))

        try:
            update_query = """
                UPDATE procedimientomascota 
                SET idmascota = %s, idprocedimiento = %s, fecha = %s, observacion = %s, idveterinario = %s
                WHERE Idregistro = %s
            """
            cursor.execute(update_query, (idmascota, idprocedimiento, fecha, observacion, idveterinario, id))
            conn.commit()
            flash('Procedimiento actualizado correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al actualizar el procedimiento: {err}', 'error')
        return redirect(url_for('gestion_procedimientos_mascotas'))
    
    # GET: Cargar datos para formulario
    try:
        # Obtener el registro actual
        cursor.execute("SELECT * FROM procedimientomascota WHERE Idregistro = %s", (id,))
        procedimiento_mascota = cursor.fetchone()
        
        if not procedimiento_mascota:
            flash('Registro no encontrado.', 'error')
            return redirect(url_for('gestion_procedimientos_mascotas'))
        
        # Obtener mascotas activas
        cursor.execute("SELECT Idmascota, nombre FROM mascota WHERE estado = TRUE ORDER BY nombre")
        mascotas = cursor.fetchall()
        
        # Obtener tipos de procedimientos activos
        cursor.execute("SELECT Idprocedimiento, nombre FROM tipoprocedimiento WHERE estado = TRUE ORDER BY nombre")
        tipos_procedimientos = cursor.fetchall()
        
        # Obtener veterinarios
        cursor.execute("""
            SELECT Idpersona, CONCAT(nom1, ' ', apell1) as nombre_completo 
            FROM persona 
            WHERE estado = TRUE 
            ORDER BY nom1, apell1
        """)
        veterinarios = cursor.fetchall()
        
        return render_template('editar_procedimiento_mascota.html', 
                             procedimiento_mascota=procedimiento_mascota,
                             mascotas=mascotas, 
                             tipos_procedimientos=tipos_procedimientos, 
                             veterinarios=veterinarios)
    except mysql.connector.Error as err:
        flash(f'Error al cargar los datos: {err}', 'error')
        return redirect(url_for('gestion_procedimientos_mascotas'))


@app.route('/procedimiento-mascota/ver/<int:id>')
def ver_procedimiento_mascota(id):
    """Ver detalles de un procedimiento aplicado a mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_procedimientos_mascotas'))
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            pm.*,
            m.nombre as nombre_mascota,
            CONCAT(due.nom1, ' ', due.apell1) as nombre_dueno,
            tp.nombre as nombre_procedimiento,
            tp.descripcion as descripcion_procedimiento,
            CONCAT(vet.nom1, ' ', vet.apell1) as nombre_veterinario
        FROM procedimientomascota pm
        JOIN mascota m ON pm.idmascota = m.Idmascota
        JOIN persona due ON m.iddueno = due.Idpersona
        JOIN tipoprocedimiento tp ON pm.idprocedimiento = tp.Idprocedimiento
        LEFT JOIN persona vet ON pm.idveterinario = vet.Idpersona
        WHERE pm.Idregistro = %s
    """, (id,))
    
    procedimiento_mascota = cursor.fetchone()
    
    if procedimiento_mascota:
        return render_template('ver_procedimiento_mascota.html', procedimiento_mascota=procedimiento_mascota)
    else:
        flash('Registro no encontrado.', 'error')
        return redirect(url_for('gestion_procedimientos_mascotas'))


@app.route('/procedimiento-mascota/inhabilitar/<int:id>')
def inhabilitar_procedimiento_mascota(id):
    """Cambiar estado activo/inactivo de un registro de procedimiento"""
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))
    
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # Consultar estado actual
            cursor.execute("SELECT estado FROM procedimientomascota WHERE Idregistro = %s", (id,))
            row = cursor.fetchone()
            
            if row is not None:
                nuevo_estado = not bool(row['estado'])
                cursor.execute(
                    "UPDATE procedimientomascota SET estado = %s WHERE Idregistro = %s", 
                    (nuevo_estado, id)
                )
                conn.commit()
                estado_texto = "habilitado" if nuevo_estado else "deshabilitado"
                flash(f'Registro {estado_texto} correctamente.', 'success')
            else:
                flash('Registro no encontrado.', 'error')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al cambiar el estado: {err}', 'error')
    
    return redirect(url_for('gestion_procedimientos_mascotas'))


# ==================== RUTA TEMPORAL PARA DEPURACIÓN ====================
@app.route('/debug-mascota-table')
def debug_mascota_table():
    """Ruta temporal para verificar la estructura de la tabla mascota"""
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))
    
    conn = get_db()
    if conn:
        cursor = conn.cursor()
        try:
            # Mostrar estructura de la tabla mascota
            cursor.execute("DESCRIBE mascota")
            columns = cursor.fetchall()
            
            # Mostrar algunos registros de ejemplo
            cursor.execute("SELECT * FROM mascota LIMIT 3")
            sample_data = cursor.fetchall()
            
            result = {
                'columns': columns,
                'sample_data': sample_data
            }
            
            flash(f'Estructura de tabla mascota: {result}', 'info')
        except mysql.connector.Error as err:
            flash(f'Error al consultar tabla mascota: {err}', 'error')
    
    return redirect(url_for('menu_principal'))


# ====== GESTIÓN DE ENFERMEDADES ======

@app.route('/enfermedades')
def gestion_enfermedades():
    """Gestión de tipos de enfermedades"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('menu_principal'))
    
    cursor = conn.cursor(dictionary=True)
    
    # Obtener filtros
    nombre_filtro = request.args.get('nombre', '').strip()
    estado_filtro = request.args.get('estado', '')
    
    # Construir consulta con filtros
    query = "SELECT * FROM tipoenfermedad WHERE 1=1"
    params = []
    
    if nombre_filtro:
        query += " AND nombre LIKE %s"
        params.append(f'%{nombre_filtro}%')
    
    if estado_filtro != '':
        query += " AND estado = %s"
        params.append(int(estado_filtro))
    
    query += " ORDER BY nombre"
    
    try:
        cursor.execute(query, params)
        enfermedades = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Error al consultar enfermedades: {err}', 'error')
        enfermedades = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('gestion_enfermedades.html', enfermedades=enfermedades)


@app.route('/enfermedad/crear', methods=['GET', 'POST'])
def crear_enfermedad():
    """Crear nueva enfermedad"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        observaciones = request.form.get('observaciones', '').strip()
        
        if not nombre:
            flash('El nombre de la enfermedad es obligatorio.', 'error')
            return redirect(url_for('crear_enfermedad'))
        
        conn = get_db()
        if not conn:
            flash('Error de conexión con la base de datos.', 'error')
            return redirect(url_for('gestion_enfermedades'))
        
        cursor = conn.cursor()
        
        try:
            # Verificar si ya existe una enfermedad con el mismo nombre
            cursor.execute("SELECT Idenfermedad FROM tipoenfermedad WHERE nombre = %s", (nombre,))
            if cursor.fetchone():
                flash('Ya existe una enfermedad con ese nombre.', 'error')
                return redirect(url_for('crear_enfermedad'))
            
            # Crear la enfermedad
            query = """
                INSERT INTO tipoenfermedad (nombre, observaciones, estado)
                VALUES (%s, %s, 1)
            """
            cursor.execute(query, (nombre, observaciones or None))
            conn.commit()
            
            flash('Enfermedad creada exitosamente.', 'success')
            return redirect(url_for('gestion_enfermedades'))
            
        except mysql.connector.Error as err:
            flash(f'Error al crear enfermedad: {err}', 'error')
            return redirect(url_for('crear_enfermedad'))
        finally:
            cursor.close()
            conn.close()
    
    return render_template('crear_enfermedad.html')


@app.route('/enfermedad/editar/<int:id>', methods=['GET', 'POST'])
def editar_enfermedad(id):
    """Editar enfermedad existente"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_enfermedades'))
    
    cursor = conn.cursor(dictionary=True)
    
    # Obtener la enfermedad actual
    try:
        cursor.execute("SELECT * FROM tipoenfermedad WHERE Idenfermedad = %s", (id,))
        enfermedad = cursor.fetchone()
        
        if not enfermedad:
            flash('Enfermedad no encontrada.', 'error')
            return redirect(url_for('gestion_enfermedades'))
    except mysql.connector.Error as err:
        flash(f'Error al buscar enfermedad: {err}', 'error')
        return redirect(url_for('gestion_enfermedades'))
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        observaciones = request.form.get('observaciones', '').strip()
        
        if not nombre:
            flash('El nombre de la enfermedad es obligatorio.', 'error')
            return render_template('editar_enfermedad.html', enfermedad=enfermedad)
        
        try:
            # Verificar si ya existe otra enfermedad con el mismo nombre
            cursor.execute("SELECT Idenfermedad FROM tipoenfermedad WHERE nombre = %s AND Idenfermedad != %s", (nombre, id))
            if cursor.fetchone():
                flash('Ya existe otra enfermedad con ese nombre.', 'error')
                return render_template('editar_enfermedad.html', enfermedad=enfermedad)
            
            # Actualizar la enfermedad
            query = """
                UPDATE tipoenfermedad 
                SET nombre = %s, observaciones = %s
                WHERE Idenfermedad = %s
            """
            cursor.execute(query, (nombre, observaciones or None, id))
            conn.commit()
            
            flash('Enfermedad actualizada exitosamente.', 'success')
            return redirect(url_for('gestion_enfermedades'))
            
        except mysql.connector.Error as err:
            flash(f'Error al actualizar enfermedad: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    cursor.close()
    conn.close()
    return render_template('editar_enfermedad.html', enfermedad=enfermedad)


@app.route('/enfermedad/inhabilitar/<int:id>')
def inhabilitar_enfermedad(id):
    """Habilitar/deshabilitar enfermedad"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Solo administradores pueden inhabilitar
    if session.get('user_profile') != 'Administrador':
        flash('No tiene permisos para realizar esta acción.', 'error')
        return redirect(url_for('gestion_enfermedades'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_enfermedades'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener estado actual
        cursor.execute("SELECT estado FROM tipoenfermedad WHERE Idenfermedad = %s", (id,))
        enfermedad = cursor.fetchone()
        
        if not enfermedad:
            flash('Enfermedad no encontrada.', 'error')
            return redirect(url_for('gestion_enfermedades'))
        
        # Cambiar estado
        nuevo_estado = 0 if enfermedad['estado'] else 1
        cursor.execute("UPDATE tipoenfermedad SET estado = %s WHERE Idenfermedad = %s", (nuevo_estado, id))
        conn.commit()
        
        accion = 'habilitada' if nuevo_estado else 'deshabilitada'
        flash(f'Enfermedad {accion} exitosamente.', 'success')
        
    except mysql.connector.Error as err:
        flash(f'Error al cambiar estado de enfermedad: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('gestion_enfermedades'))


# ====== GESTIÓN DE ENFERMEDADES DE MASCOTAS ======

@app.route('/enfermedades-mascotas')
def gestion_enfermedades_mascotas():
    """Gestión del historial de enfermedades de mascotas"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('menu_principal'))
    
    cursor = conn.cursor(dictionary=True)
    
    # Obtener filtros
    mascota_filtro = request.args.get('mascota', '').strip()
    enfermedad_filtro = request.args.get('enfermedad', '').strip()
    fecha_desde = request.args.get('fecha_desde', '').strip()
    fecha_hasta = request.args.get('fecha_hasta', '').strip()
    
    # Construir consulta con filtros
    query = """
        SELECT me.id, me.idmascota, me.idenfermedad, me.fecha,
               m.nombre as nombre_mascota, te.nombre as nombre_enfermedad,
               CASE 
                   WHEN EXISTS(SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'mascotaenfermedad' AND COLUMN_NAME = 'estado') 
                   THEN me.estado 
                   ELSE TRUE 
               END as estado
        FROM mascotaenfermedad me
        JOIN mascota m ON me.idmascota = m.Idmascota
        JOIN tipoenfermedad te ON me.idenfermedad = te.Idenfermedad
        WHERE 1=1
    """
    params = []
    
    if mascota_filtro:
        query += " AND m.nombre LIKE %s"
        params.append(f'%{mascota_filtro}%')
    
    if enfermedad_filtro:
        query += " AND te.nombre LIKE %s"
        params.append(f'%{enfermedad_filtro}%')
    
    if fecha_desde:
        query += " AND me.fecha >= %s"
        params.append(fecha_desde)
    
    if fecha_hasta:
        query += " AND me.fecha <= %s"
        params.append(fecha_hasta)
    
    query += " ORDER BY me.fecha DESC, m.nombre"
    
    try:
        cursor.execute(query, params)
        enfermedades_mascotas = cursor.fetchall()
    except mysql.connector.Error as err:
        flash(f'Error al consultar enfermedades de mascotas: {err}', 'error')
        enfermedades_mascotas = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('gestion_enfermedades_mascotas.html', enfermedades_mascotas=enfermedades_mascotas)


@app.route('/enfermedad-mascota/crear', methods=['GET', 'POST'])
def crear_enfermedad_mascota():
    """Registrar nueva enfermedad de mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        idmascota = request.form.get('idmascota')
        idenfermedad = request.form.get('idenfermedad')
        fecha = request.form.get('fecha')
        observacion = request.form.get('observacion', '').strip()
        
        if not idmascota or not idenfermedad:
            flash('Mascota y enfermedad son obligatorios.', 'error')
            return redirect(url_for('crear_enfermedad_mascota'))
        
        conn = get_db()
        if not conn:
            flash('Error de conexión con la base de datos.', 'error')
            return redirect(url_for('gestion_enfermedades_mascotas'))
        
        cursor = conn.cursor()
        
        try:
            # Crear el registro de enfermedad de mascota
            query = """
                INSERT INTO mascotaenfermedad (idmascota, idenfermedad, fecha, observacion)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (idmascota, idenfermedad, fecha or None, observacion or None))
            conn.commit()
            
            flash('Enfermedad de mascota registrada exitosamente.', 'success')
            return redirect(url_for('gestion_enfermedades_mascotas'))
            
        except mysql.connector.Error as err:
            flash(f'Error al registrar enfermedad de mascota: {err}', 'error')
            return redirect(url_for('crear_enfermedad_mascota'))
        finally:
            cursor.close()
            conn.close()
    
    # Obtener datos para el formulario
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener mascotas activas
        cursor.execute("SELECT Idmascota, nombre FROM mascota WHERE estado = 1 ORDER BY nombre")
        mascotas = cursor.fetchall()
        
        # Obtener enfermedades activas
        cursor.execute("SELECT Idenfermedad, nombre FROM tipoenfermedad WHERE estado = 1 ORDER BY nombre")
        enfermedades = cursor.fetchall()
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar datos: {err}', 'error')
        mascotas = []
        enfermedades = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('crear_enfermedad_mascota.html', mascotas=mascotas, enfermedades=enfermedades)


@app.route('/enfermedad-mascota/editar/<int:id>', methods=['GET', 'POST'])
def editar_enfermedad_mascota(id):
    """Editar registro de enfermedad de mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    cursor = conn.cursor(dictionary=True)
    
    # Obtener el registro actual
    try:
        cursor.execute("""
            SELECT me.*, m.nombre as nombre_mascota, te.nombre as nombre_enfermedad
            FROM mascotaenfermedad me
            JOIN mascota m ON me.idmascota = m.Idmascota
            JOIN tipoenfermedad te ON me.idenfermedad = te.Idenfermedad
            WHERE me.id = %s
        """, (id,))
        enfermedad_mascota = cursor.fetchone()
        
        if not enfermedad_mascota:
            flash('Registro no encontrado.', 'error')
            return redirect(url_for('gestion_enfermedades_mascotas'))
    except mysql.connector.Error as err:
        flash(f'Error al buscar registro: {err}', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    if request.method == 'POST':
        idmascota = request.form.get('idmascota')
        idenfermedad = request.form.get('idenfermedad')
        fecha = request.form.get('fecha')
        observacion = request.form.get('observacion', '').strip()
        
        if not idmascota or not idenfermedad:
            flash('Mascota y enfermedad son obligatorios.', 'error')
        else:
            try:
                # Actualizar el registro
                query = """
                    UPDATE mascotaenfermedad 
                    SET idmascota = %s, idenfermedad = %s, fecha = %s, observacion = %s
                    WHERE id = %s
                """
                cursor.execute(query, (idmascota, idenfermedad, fecha or None, observacion or None, id))
                conn.commit()
                
                flash('Registro actualizado exitosamente.', 'success')
                return redirect(url_for('gestion_enfermedades_mascotas'))
                
            except mysql.connector.Error as err:
                flash(f'Error al actualizar registro: {err}', 'error')
    
    # Obtener datos para el formulario
    try:
        # Obtener mascotas activas
        cursor.execute("SELECT Idmascota, nombre FROM mascota WHERE estado = 1 ORDER BY nombre")
        mascotas = cursor.fetchall()
        
        # Obtener enfermedades activas
        cursor.execute("SELECT Idenfermedad, nombre FROM tipoenfermedad WHERE estado = 1 ORDER BY nombre")
        enfermedades = cursor.fetchall()
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar datos: {err}', 'error')
        mascotas = []
        enfermedades = []
    finally:
        cursor.close()
        conn.close()
    
    return render_template('editar_enfermedad_mascota.html', 
                         enfermedad_mascota=enfermedad_mascota, 
                         mascotas=mascotas, 
                         enfermedades=enfermedades)


@app.route('/enfermedad-mascota/ver/<int:id>')
def ver_enfermedad_mascota(id):
    """Ver detalles de registro de enfermedad de mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT me.*, m.nombre as nombre_mascota, r.nombre as raza, 
                   TIMESTAMPDIFF(YEAR, m.fecha_nac, CURDATE()) as edad,
                   te.nombre as nombre_enfermedad, te.observaciones as observaciones_enfermedad,
                   (SELECT c.peso FROM consulta c 
                    WHERE c.idhistoria = (SELECT h.Idhistoria FROM historia_clinica h WHERE h.idmascota = m.Idmascota LIMIT 1)
                    AND c.peso IS NOT NULL 
                    ORDER BY c.fecha_consulta DESC, c.Idconsulta DESC 
                    LIMIT 1) as peso
            FROM mascotaenfermedad me
            JOIN mascota m ON me.idmascota = m.Idmascota
            JOIN raza r ON m.idraza = r.Idraza
            JOIN tipoenfermedad te ON me.idenfermedad = te.Idenfermedad
            WHERE me.id = %s
        """, (id,))
        enfermedad_mascota = cursor.fetchone()
        
        if not enfermedad_mascota:
            flash('Registro no encontrado.', 'error')
            return redirect(url_for('gestion_enfermedades_mascotas'))
            
    except mysql.connector.Error as err:
        flash(f'Error al buscar registro: {err}', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    finally:
        cursor.close()
        conn.close()
    
    return render_template('ver_enfermedad_mascota.html', enfermedad_mascota=enfermedad_mascota)


@app.route('/enfermedad-mascota/eliminar/<int:id>')
def eliminar_enfermedad_mascota(id):
    """Deshabilitar registro de enfermedad de mascota (soft delete)"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Solo administradores pueden deshabilitar
    if session.get('user_profile') != 'Administrador':
        flash('No tiene permisos para realizar esta acción.', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    cursor = conn.cursor()
    
    try:
        # Verificar que existe el registro
        cursor.execute("SELECT id FROM mascotaenfermedad WHERE id = %s", (id,))
        if not cursor.fetchone():
            flash('Registro no encontrado.', 'error')
            return redirect(url_for('gestion_enfermedades_mascotas'))
        
        # Primero intentar agregar la columna estado si no existe
        try:
            cursor.execute("ALTER TABLE mascotaenfermedad ADD COLUMN estado BOOLEAN DEFAULT TRUE")
            conn.commit()
        except mysql.connector.Error:
            # La columna ya existe, continuar
            pass
        
        # Hacer soft delete
        cursor.execute("UPDATE mascotaenfermedad SET estado = FALSE WHERE id = %s", (id,))
        conn.commit()
        
        flash('Registro deshabilitado exitosamente.', 'success')
        
    except mysql.connector.Error as err:
        flash(f'Error al eliminar registro: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('gestion_enfermedades_mascotas'))

@app.route('/enfermedad-mascota/habilitar/<int:id>', methods=['GET'])
def habilitar_enfermedad_mascota(id):
    """Habilitar registro de enfermedad de mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Solo administradores pueden habilitar
    if session.get('user_profile') != 'Administrador':
        flash('No tiene permisos para realizar esta acción.', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_enfermedades_mascotas'))
    
    cursor = conn.cursor()
    
    try:
        # Verificar que existe el registro
        cursor.execute("SELECT id FROM mascotaenfermedad WHERE id = %s", (id,))
        if not cursor.fetchone():
            flash('Registro no encontrado.', 'error')
            return redirect(url_for('gestion_enfermedades_mascotas'))
        
        # Primero intentar agregar la columna estado si no existe
        try:
            cursor.execute("ALTER TABLE mascotaenfermedad ADD COLUMN estado BOOLEAN DEFAULT TRUE")
            conn.commit()
        except mysql.connector.Error:
            # La columna ya existe, continuar
            pass
        
        # Habilitar el registro
        cursor.execute("UPDATE mascotaenfermedad SET estado = TRUE WHERE id = %s", (id,))
        conn.commit()
        
        flash('Registro habilitado exitosamente.', 'success')
        
    except mysql.connector.Error as err:
        flash(f'Error al habilitar registro: {err}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('gestion_enfermedades_mascotas'))

@app.route('/razas')
def gestion_razas():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    razas = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM raza ORDER BY nombre ASC")
        razas = cursor.fetchall()
    return render_template('gestion_razas.html', razas=razas)

@app.route('/raza/crear', methods=['POST'])
def crear_raza():
    if 'user_id' not in session: return redirect(url_for('login'))
    nombre = request.form['nombre']
    conn = get_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO raza (nombre) VALUES (%s)", (nombre,))
            conn.commit()
            flash('Raza creada exitosamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al crear la raza: {err}', 'error')
    return redirect(url_for('gestion_razas'))

@app.route('/raza/editar/<int:id>', methods=['GET', 'POST'])
def editar_raza(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        nombre = request.form['nombre']
        try:
            cursor.execute("UPDATE raza SET nombre = %s WHERE Idraza = %s", (nombre, id))
            conn.commit()
            flash('Raza actualizada correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al actualizar la raza: {err}', 'error')
        return redirect(url_for('gestion_razas'))
    
    cursor.execute("SELECT * FROM raza WHERE Idraza = %s", (id,))
    raza = cursor.fetchone()
    if raza:
        return render_template('editar_raza.html', raza=raza)
    return redirect(url_for('gestion_razas'))

@app.route('/raza/inhabilitar/<int:id>')
def inhabilitar_raza(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    try:
        cursor = conn.cursor()
        # Aquí se podría añadir una validación para no inhabilitar si hay mascotas de esa raza
        cursor.execute("UPDATE raza SET estado = NOT estado WHERE Idraza = %s", (id,))
        conn.commit()
        flash('Estado de la raza cambiado correctamente.', 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Error al cambiar el estado: {err}', 'error')
    return redirect(url_for('gestion_razas'))


# --- GESTIÓN DE MASCOTAS ---

@app.route('/mascotas')
def gestion_mascotas():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    mascotas = []
    razas = []
    duenios = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        
        # Query para obtener la lista de mascotas con nombres de raza, dueño y edad
        mascotas_query = """
            SELECT m.Idmascota, m.nombre, m.estado, 
                   TIMESTAMPDIFF(YEAR, m.fecha_nac, CURDATE()) as edad, 
                   r.nombre AS raza_nombre, p.nom1 AS duenio_nombre
            FROM mascota m
            JOIN raza r ON m.idraza = r.Idraza
            JOIN persona p ON m.idduenio = p.Idpersona
            ORDER BY m.nombre ASC
        """
        cursor.execute(mascotas_query)
        mascotas = cursor.fetchall()
        
        # Queries para poblar los dropdowns del formulario de creación
        cursor.execute("SELECT Idraza, nombre FROM raza WHERE estado = 1 ORDER BY nombre ASC")
        razas = cursor.fetchall()
        
        # Filtrar solo personas que tienen perfil de veterinario (idperfil = 6)
        duenios_query = """
            SELECT p.Idpersona, p.nom1, p.apell1 
            FROM persona p
            JOIN usuario u ON p.Idpersona = u.idpersona
            WHERE p.estado = 1 AND u.idperfil = 6
            ORDER BY p.nom1 ASC
        """
        cursor.execute(duenios_query)
        duenios = cursor.fetchall()

    return render_template('gestion_mascotas.html', mascotas=mascotas, razas=razas, duenios=duenios)

@app.route('/mascota/crear', methods=['POST'])
def crear_mascota():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    try:
        cursor = conn.cursor()
        
        # Calcular edad si se proporciona fecha de nacimiento
        fecha_nac = request.form.get('fecha_nac') or None
        edad = None
        if fecha_nac:
            from datetime import datetime
            fecha_nacimiento = datetime.strptime(fecha_nac, '%Y-%m-%d')
            fecha_actual = datetime.now()
            edad_timedelta = fecha_actual - fecha_nacimiento
            edad = edad_timedelta.days // 365  # Edad en años
        
        query = """
            INSERT INTO mascota (codigo, nombre, fecha_nac, caracteristicas, idraza, idduenio, edad)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            request.form['codigo'], request.form['nombre'], fecha_nac,
            request.form.get('caracteristicas'), request.form['idraza'], request.form['idduenio'], edad
        ))
        conn.commit()
        flash('Mascota registrada exitosamente.', 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        if err.errno == 1062: # Error de entrada duplicada para el código/chip
            flash('Error: El código o chip de la mascota ya está registrado.', 'error')
        else:
            flash(f'Error al registrar la mascota: {err}', 'error')
    return redirect(url_for('gestion_mascotas'))

@app.route('/mascota/editar/<int:id>', methods=['GET', 'POST'])
def editar_mascota(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            # Calcular edad si se proporciona fecha de nacimiento
            fecha_nac = request.form.get('fecha_nac') or None
            edad = None
            if fecha_nac:
                from datetime import datetime
                fecha_nacimiento = datetime.strptime(fecha_nac, '%Y-%m-%d')
                fecha_actual = datetime.now()
                edad_timedelta = fecha_actual - fecha_nacimiento
                edad = edad_timedelta.days // 365  # Edad en años
            
            query = """
                UPDATE mascota SET
                codigo = %s, nombre = %s, fecha_nac = %s, caracteristicas = %s,
                idraza = %s, idduenio = %s, edad = %s
                WHERE Idmascota = %s
            """
            cursor.execute(query, (
                request.form['codigo'], request.form['nombre'], fecha_nac,
                request.form.get('caracteristicas'), request.form['idraza'], request.form['idduenio'], edad, id
            ))
            conn.commit()
            flash('Datos de la mascota actualizados correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al actualizar la mascota: {err}', 'error')
        return redirect(url_for('gestion_mascotas'))

    # Lógica para GET
    cursor.execute("SELECT * FROM mascota WHERE Idmascota = %s", (id,))
    mascota = cursor.fetchone()
    
    cursor.execute("SELECT Idraza, nombre FROM raza WHERE estado = 1 ORDER BY nombre ASC")
    razas = cursor.fetchall()
    
    # Filtrar solo personas que tienen perfil de veterinario (idperfil = 6)
    duenios_query = """
        SELECT p.Idpersona, p.nom1, p.apell1 
        FROM persona p
        JOIN usuario u ON p.Idpersona = u.idpersona
        WHERE p.estado = 1 AND u.idperfil = 6
        ORDER BY p.nom1 ASC
    """
    cursor.execute(duenios_query)
    duenios = cursor.fetchall()

    if mascota:
        return render_template('editar_mascota.html', mascota=mascota, razas=razas, duenios=duenios)
    return redirect(url_for('gestion_mascotas'))

@app.route('/mascota/inhabilitar/<int:id>')
def inhabilitar_mascota(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE mascota SET estado = NOT estado WHERE Idmascota = %s", (id,))
        conn.commit()
        flash('Estado de la mascota cambiado correctamente.', 'success')
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Error al cambiar el estado: {err}', 'error')
    return redirect(url_for('gestion_mascotas'))

@app.route('/asignar_mascota', methods=['POST'])
def asignar_mascota():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    idusuario = request.form.get('idusuario')
    idmascota = request.form.get('idmascota')

    # Validaciones
    if not idusuario or not idmascota:
        flash('Debe seleccionar tanto un veterinario como una mascota.', 'error')
        return redirect(url_for('gestion_veterinarios'))

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_veterinarios'))

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Verificar que el usuario existe, está activo y es veterinario (idperfil = 6)
        cursor.execute("SELECT Idusuario, nombreu FROM Usuario WHERE Idusuario = %s AND estado = 1 AND idperfil = 6", (idusuario,))
        usuario = cursor.fetchone()
        if not usuario:
            flash('El usuario seleccionado no es un veterinario válido.', 'error')
            return redirect(url_for('gestion_veterinarios'))
            flash('El usuario veterinario seleccionado no es válido o está inactivo.', 'error')
            return redirect(url_for('gestion_veterinarios'))
        
        # Verificar que la mascota existe y está activa
        cursor.execute("SELECT Idmascota, nombre FROM mascota WHERE Idmascota = %s AND estado = 1", (idmascota,))
        mascota = cursor.fetchone()
        if not mascota:
            flash('La mascota seleccionada no es válida o está inactiva.', 'error')
            return redirect(url_for('gestion_veterinarios'))
        
        # Verificar si la mascota ya tiene un veterinario asignado
        cursor.execute("SELECT idveterinario FROM mascota WHERE Idmascota = %s", (idmascota,))
        current_assignment = cursor.fetchone()
        if current_assignment['idveterinario'] is not None:
            flash(f'La mascota "{mascota["nombre"]}" ya tiene un veterinario asignado. Se actualizará la asignación.', 'warning')
        
        # Realizar la asignación
        cursor.execute("UPDATE mascota SET idveterinario = %s WHERE Idmascota = %s", (idusuario, idmascota))
        conn.commit()
        
        flash(f'Mascota "{mascota["nombre"]}" asignada exitosamente al veterinario "{usuario["nombreu"]}"', 'success')
        
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Error al asignar la mascota: {err}', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('gestion_veterinarios'))


@app.route('/desasignar_mascota/<int:idmascota>', methods=['POST'])
def desasignar_mascota(idmascota):
    """Desasignar una mascota de su veterinario actual"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_veterinarios'))

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Obtener información de la mascota antes de desasignar
        cursor.execute("""
            SELECT m.nombre, CONCAT(p.nom1, ' ', p.apell1) as veterinario_nombre
            FROM mascota m
            LEFT JOIN Usuario u ON m.idveterinario = u.Idusuario
            LEFT JOIN Persona p ON u.idpersona = p.Idpersona
            WHERE m.Idmascota = %s
        """, (idmascota,))
        mascota_info = cursor.fetchone()
        
        if not mascota_info:
            flash('Mascota no encontrada.', 'error')
            return redirect(url_for('gestion_veterinarios'))
        
        # Desasignar la mascota
        cursor.execute("UPDATE mascota SET idveterinario = NULL WHERE Idmascota = %s", (idmascota,))
        conn.commit()
        
        veterinario_nombre = mascota_info['veterinario_nombre'] or 'Sin asignar'
        flash(f'Mascota "{mascota_info["nombre"]}" desasignada exitosamente del veterinario "{veterinario_nombre}"', 'success')
        
    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Error al desasignar la mascota: {err}', 'error')
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for('gestion_veterinarios'))


@app.route('/citas')
def gestion_citas():
    """Muestra el formulario para crear citas y la lista de citas programadas."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('menu_principal'))
    
    cursor = conn.cursor(dictionary=True)
    try:
        # Cargar datos para los formularios
        cursor.execute("SELECT Idmascota, nombre FROM mascota WHERE estado = 1 ORDER BY nombre")
        mascotas = cursor.fetchall()

        cursor.execute("""
            SELECT p.Idpersona, CONCAT(p.nom1, ' ', p.apell1) AS nombre_completo
            FROM persona p
            JOIN usuario u ON p.Idpersona = u.Idpersona
            JOIN perfil pr ON u.idperfil = pr.Idperfil
            WHERE pr.descripc IN ('Administrador', 'empleado') AND p.estado = 1
        """)
        veterinarios = cursor.fetchall()

        # Cargar citas futuras
        cursor.execute("""
            SELECT c.Idcita, m.nombre AS nombre_mascota, p_duenio.correo AS duenio_email,
                   CONCAT(p_vet.nom1, ' ', p_vet.apell1) AS nombre_veterinario,
                   c.fecha, c.motivo
            FROM cita c
            JOIN mascota m ON c.idmascota = m.Idmascota
            JOIN persona p_duenio ON c.idduenio = p_duenio.Idpersona
            JOIN persona p_vet ON c.idveterinario = p_vet.Idpersona
            WHERE c.fecha >= CURDATE() AND c.estado = 1
            ORDER BY c.fecha ASC
        """)
        citas = cursor.fetchall()
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar datos: {err}', 'error')
        mascotas, veterinarios, citas = [], [], []
    finally:
        cursor.close()
        conn.close()

    return render_template('gestion_citas.html', mascotas=mascotas, veterinarios=veterinarios, citas=citas)


@app.route('/cita/crear', methods=['POST'])
def crear_cita():
    """Crea una nueva cita y envía un correo de confirmación."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    idmascota = request.form.get('idmascota')
    idveterinario = request.form.get('idveterinario')
    fecha_str = request.form.get('fecha')
    hora_str = request.form.get('hora')
    motivo = request.form.get('motivo')

    if not all([idmascota, idveterinario, fecha_str, hora_str, motivo]):
        flash('Todos los campos son obligatorios.', 'error')
        return redirect(url_for('gestion_citas'))

    fecha_hora_str = f"{fecha_str} {hora_str}"
    fecha_hora_obj = datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M')

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        # Obtener el id del dueño (idduenio) desde la tabla mascota
        cursor.execute("SELECT idduenio FROM mascota WHERE Idmascota = %s", (idmascota,))
        mascota = cursor.fetchone()
        if not mascota:
            flash('Mascota no encontrada.', 'error')
            return redirect(url_for('gestion_citas'))
        idduenio = mascota['idduenio']
        
        # Insertar la cita
        query = """
            INSERT INTO cita (idmascota, idduenio, idveterinario, fecha, motivo, estado)
            VALUES (%s, %s, %s, %s, %s, 1)
        """
        cursor.execute(query, (idmascota, idduenio, idveterinario, fecha_hora_obj, motivo))
        conn.commit()
        
        # Enviar correo de confirmación
        enviar_correo_cita(idmascota, fecha_hora_obj, motivo, "Confirmación de Cita en MediPet")
        
        flash('Cita creada y correo de confirmación enviado exitosamente.', 'success')

    except mysql.connector.Error as err:
        conn.rollback()
        flash(f'Error al crear la cita: {err}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('gestion_citas'))


def enviar_correo_cita(idmascota, fecha_hora_obj, motivo, asunto):
    """Función genérica para enviar correos relacionados con citas."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener datos necesarios para el correo
    cursor.execute("""
        SELECT m.nombre AS nombre_mascota, p.nom1 AS nombre_duenio, p.correo AS email_duenio
        FROM mascota m
        JOIN persona p ON m.idduenio = p.Idpersona
        WHERE m.Idmascota = %s
    """, (idmascota,))
    datos = cursor.fetchone()
    cursor.close()
    conn.close()

    if not datos or not datos['email_duenio']:
        print(f"No se pudo enviar correo para mascota ID {idmascota}: sin datos o email.")
        return

    # Formatear la fecha y hora para el correo
    fecha_formateada = fecha_hora_obj.strftime('%d de %B de %Y')
    hora_formateada = fecha_hora_obj.strftime('%I:%M %p')

    # Renderizar el cuerpo del correo desde una plantilla HTML
    html_body = render_template('email/notificacion_cita.html',
                                nombre_duenio=datos['nombre_duenio'],
                                nombre_mascota=datos['nombre_mascota'],
                                fecha=fecha_formateada,
                                hora=hora_formateada,
                                motivo=motivo,
                                asunto=asunto)

    msg = Message(asunto, recipients=[datos['email_duenio']])
    msg.html = html_body
    
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        
def validar_cedula(ced):
    ced = (ced or "").strip()
    if not ced:
        return "La cédula es obligatoria."
    if len(ced) > 20:
        return "La cédula admite máximo 20 caracteres."
    # Si quieres solo dígitos, usa: r'^\d+$'
    if not re.match(r'^[0-9A-Za-z.\-]+$', ced):
        return "La cédula solo puede contener números/letras y . -"
    return None


# ==================== MÓDULO DE HISTORIAS CLÍNICAS ====================

@app.route('/gestion_historias_clinicas')
def gestion_historias_clinicas():
    """Gestión principal de historias clínicas"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('menu_principal'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Obtener estadísticas básicas
        cursor.execute("SELECT COUNT(*) as total FROM historia_clinica WHERE estado = TRUE")
        total_historias = cursor.fetchone()['total'] or 0
        
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM consulta 
            WHERE estado = TRUE 
            AND DATE(fecha_consulta) = CURDATE()
        """)
        consultas_hoy = cursor.fetchone()['total'] or 0
        
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM consulta 
            WHERE estado = TRUE 
            AND MONTH(fecha_consulta) = MONTH(CURDATE()) 
            AND YEAR(fecha_consulta) = YEAR(CURDATE())
        """)
        consultas_mes = cursor.fetchone()['total'] or 0
        
        # Obtener todas las historias clínicas con información de mascotas
        query = """
            SELECT 
                hc.Idhistoria,
                hc.fecha_apertura,
                m.nombre as nombre_mascota,
                m.codigo as codigo_mascota,
                r.nombre as raza,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_responsable,
                (SELECT COUNT(*) FROM consulta c WHERE c.idhistoria = hc.Idhistoria AND c.estado = TRUE) as total_consultas,
                (SELECT MAX(fecha_consulta) FROM consulta c WHERE c.idhistoria = hc.Idhistoria AND c.estado = TRUE) as ultima_consulta,
                hc.estado
            FROM historia_clinica hc
            JOIN mascota m ON hc.idmascota = m.Idmascota
            JOIN raza r ON m.idraza = r.Idraza
            JOIN persona p ON m.idduenio = p.Idpersona
            LEFT JOIN Usuario u ON hc.veterinario_responsable = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE hc.estado = TRUE
            ORDER BY hc.fecha_apertura DESC, hc.Idhistoria DESC
        """
        cursor.execute(query)
        historias = cursor.fetchall()
        
    except mysql.connector.Error as err:
        flash(f'Error al consultar historias clínicas: {err}', 'error')
        historias = []
        total_historias = 0
        consultas_hoy = 0
        consultas_mes = 0
    finally:
        cursor.close()
        conn.close()
    
    return render_template('gestion_historias_clinicas.html', 
                         historias=historias,
                         total_historias=total_historias,
                         consultas_hoy=consultas_hoy,
                         consultas_mes=consultas_mes)


@app.route('/crear_historia_clinica', methods=['GET', 'POST'])
def crear_historia_clinica():
    """Crear nueva historia clínica para una mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_historias_clinicas'))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            idmascota = request.form['idmascota']
            fecha_apertura = request.form['fecha_apertura']
            motivo_apertura = request.form['motivo_apertura']
            veterinario_responsable = request.form.get('veterinario_responsable') or session['user_id']
            estado_general = request.form.get('estado_general', '')
            prioridad = request.form.get('prioridad', 'Rutina')
            observaciones_iniciales = request.form.get('observaciones_iniciales', '')
            
            # Validaciones
            if not idmascota or not fecha_apertura or not motivo_apertura:
                flash('Mascota, fecha de apertura y motivo son obligatorios.', 'error')
                return redirect(url_for('crear_historia_clinica'))
            
            # Verificar si ya existe una historia clínica activa para esta mascota
            cursor.execute("""
                SELECT Idhistoria 
                FROM historia_clinica 
                WHERE idmascota = %s AND estado = TRUE
            """, (idmascota,))
            
            historia_existente = cursor.fetchone()
            if historia_existente:
                flash('Ya existe una historia clínica activa para esta mascota.', 'error')
                return redirect(url_for('crear_historia_clinica'))
            
            # Insertar nueva historia clínica
            query = """
                INSERT INTO historia_clinica (
                    idmascota, fecha_apertura, veterinario_responsable, 
                    motivo_apertura, estado_general, prioridad, 
                    observaciones_iniciales, estado
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                idmascota, fecha_apertura, veterinario_responsable,
                motivo_apertura, estado_general, prioridad,
                observaciones_iniciales, True
            ))
            
            historia_id = cursor.lastrowid
            conn.commit()
            
            flash('Historia clínica creada exitosamente.', 'success')
            return redirect(url_for('ver_historia_clinica', id=historia_id))
            
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al crear historia clínica: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    # GET: Cargar datos para formulario
    try:
        # Obtener mascotas que NO tienen historia clínica activa
        cursor.execute("""
            SELECT 
                m.Idmascota,
                m.nombre,
                m.codigo,
                m.sexo,
                r.nombre as raza,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario,
                CASE 
                    WHEN m.fecha_nac IS NOT NULL THEN 
                        CONCAT(TIMESTAMPDIFF(YEAR, m.fecha_nac, CURDATE()), ' años')
                    ELSE 'No especificada'
                END as edad
            FROM mascota m
            JOIN persona p ON m.idduenio = p.Idpersona
            LEFT JOIN raza r ON m.idraza = r.Idraza
            WHERE m.estado = TRUE 
            AND m.Idmascota NOT IN (
                SELECT idmascota FROM historia_clinica WHERE estado = TRUE
            )
            ORDER BY m.nombre
        """)
        mascotas = cursor.fetchall()
        
        # Obtener veterinarios disponibles
        cursor.execute("""
            SELECT 
                u.Idusuario,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_completo
            FROM Usuario u
            JOIN persona p ON u.idpersona = p.Idpersona
            JOIN Perfil pr ON u.idperfil = pr.Idperfil
            WHERE u.estado = TRUE 
            AND (pr.descripc = 'Veterinario' OR pr.descripc = 'Administrador')
            ORDER BY p.nom1, p.apell1
        """)
        veterinarios = cursor.fetchall()
        
        fecha_actual = date.today().strftime('%Y-%m-%d')
        
        return render_template('crear_historia_clinica.html', 
                             mascotas=mascotas, 
                             veterinarios=veterinarios,
                             fecha_actual=fecha_actual)
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar datos: {err}', 'error')
        return redirect(url_for('gestion_historias_clinicas'))
    finally:
        cursor.close()
        conn.close()


@app.route('/historia-clinica/<int:id>/enviar-pdf')
def enviar_historia_clinica_pdf(id):
    """Enviar por correo electrónico el PDF de la historia clínica"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Verificar que existe la historia clínica y obtener correo del dueño
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('ver_historia_clinica', id=id))
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT h.Idhistoria, m.nombre as nombre_mascota, p.correo as correo_propietario, 
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario,
                m.Idmascota as idmascota,
                m.codigo as codigo_mascota,
                m.sexo,
                m.fecha_nac,
                TIMESTAMPDIFF(YEAR, m.fecha_nac, CURDATE()) as edad_años,
                TIMESTAMPDIFF(MONTH, m.fecha_nac, CURDATE()) % 12 as edad_meses,
                r.nombre as raza,
                p.tele as telefono_propietario,
                p.direccion as direccion_propietario,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_responsable,
                h.fecha_apertura,
                h.motivo_apertura
            FROM historia_clinica h
            JOIN mascota m ON h.idmascota = m.Idmascota
            JOIN raza r ON m.idraza = r.Idraza
            JOIN persona p ON m.idduenio = p.Idpersona
            LEFT JOIN Usuario u ON h.veterinario_responsable = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE h.Idhistoria = %s
        """, (id,))
        
        historia = cursor.fetchone()
        
        if not historia:
            flash('Historia clínica no encontrada.', 'error')
            return redirect(url_for('gestion_historias_clinicas'))
        
        if not historia['correo_propietario']:
            flash('El propietario no tiene correo electrónico registrado.', 'error')
            return redirect(url_for('ver_historia_clinica', id=id))
        
        # Consultas asociadas
        cursor.execute("""
            SELECT 
                c.*,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_consulta
            FROM consulta c
            LEFT JOIN Usuario u ON c.veterinario_consulta = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE c.idhistoria = %s AND c.estado = TRUE
            ORDER BY c.fecha_consulta DESC, c.Idconsulta DESC
        """, (id,))
        consultas = cursor.fetchall()
        
        # Para cada consulta, obtener datos adicionales detallados
        for consulta in consultas:
            # Procedimientos de esta mascota
            cursor.execute("""
                SELECT 
                    pm.*,
                    tp.nombre as nombre_procedimiento,
                    CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_nombre
                FROM procedimientomascota pm
                JOIN tipoprocedimiento tp ON pm.idprocedimiento = tp.Idprocedimiento
                LEFT JOIN persona vet ON pm.idveterinario = vet.Idpersona
                WHERE pm.idmascota = %s AND pm.estado = TRUE
                AND pm.fecha BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND DATE_ADD(%s, INTERVAL 1 DAY)
                ORDER BY pm.fecha DESC
            """, (historia['idmascota'], consulta['fecha_consulta'], consulta['fecha_consulta']))
            consulta['procedimientos'] = cursor.fetchall()
            
            # Medicamentos prescritos en esta consulta específica
            cursor.execute("""
                SELECT 
                    mp.*,
                    med.nombre as nombre_medicamento
                FROM medicamento_prescrito mp
                JOIN medicamento med ON mp.idmedicamento = med.Idmedicamento
                WHERE mp.idconsulta = %s
                ORDER BY mp.fecha_inicio DESC
            """, (consulta['Idconsulta'],))
            consulta['medicamentos_consulta'] = cursor.fetchall()
            
            # Enfermedades diagnosticadas en esta consulta
            cursor.execute("""
                SELECT 
                    ed.*,
                    te.nombre as nombre_enfermedad
                FROM enfermedad_diagnosticada ed
                JOIN tipoenfermedad te ON ed.idenfermedad = te.Idenfermedad
                WHERE ed.idconsulta = %s
                ORDER BY ed.fecha_diagnostico DESC
            """, (consulta['Idconsulta'],))
            consulta['enfermedades_consulta'] = cursor.fetchall()
        
        # Medicamentos prescritos (historial general)
        cursor.execute("""
            SELECT 
                mp.*,
                med.nombre as nombre_medicamento,
                c.fecha_consulta
            FROM medicamento_prescrito mp
            JOIN medicamento med ON mp.idmedicamento = med.Idmedicamento
            JOIN consulta c ON mp.idconsulta = c.Idconsulta
            WHERE c.idhistoria = %s
            ORDER BY c.fecha_consulta DESC, mp.fecha_inicio DESC
        """, (id,))
        medicamentos = cursor.fetchall()
        
        # Vacunaciones
        cursor.execute("""
            SELECT 
                vh.*,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_aplicador
            FROM vacunacion_historia vh
            LEFT JOIN Usuario u ON vh.veterinario_aplicador = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE vh.idhistoria = %s AND vh.estado = TRUE
            ORDER BY vh.fecha_aplicacion DESC
        """, (id,))
        vacunas = cursor.fetchall()
        
        # Enfermedades diagnosticadas
        cursor.execute("""
            SELECT 
                ed.*,
                te.nombre as nombre_enfermedad,
                c.fecha_consulta
            FROM enfermedad_diagnosticada ed
            JOIN tipoenfermedad te ON ed.idenfermedad = te.Idenfermedad
            JOIN consulta c ON ed.idconsulta = c.Idconsulta
            WHERE c.idhistoria = %s
            ORDER BY c.fecha_consulta DESC, ed.fecha_diagnostico DESC
        """, (id,))
        enfermedades = cursor.fetchall()
        
        # Ahora generamos el PDF y enviamos el correo
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from datetime import datetime
        import io
        
        # Generar PDF con diseño profesional
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=50, leftMargin=50,
                              topMargin=50, bottomMargin=50)
        
        # Estilos mejorados con diseño profesional
        styles = getSampleStyleSheet()
        
        # Estilo para el header principal
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=20,
            textColor=colors.HexColor('#1e3a8a'),
            fontName='Helvetica-Bold',
            alignment=1,  # Centrado
            spaceAfter=10
        )
        
        # Estilo para subtítulos principales
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f2937'),
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=colors.HexColor('#3b82f6'),
            borderPadding=5,
            backColor=colors.HexColor('#f0f9ff'),
            leftIndent=10,
            spaceAfter=15,
            spaceBefore=20
        )
        
        # Estilo para subsecciones
        subsection_style = ParagraphStyle(
            'SubsectionStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
            spaceBefore=10
        )
        
        # Estilo para texto normal
        normal_text_style = ParagraphStyle(
            'NormalText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=6,
            alignment=4  # Justificado
        )
        
        # Estilo para información destacada
        highlight_style = ParagraphStyle(
            'HighlightStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#131414"),
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#ecfdf5'),
            borderWidth=1,
            borderColor=colors.HexColor('#10b981'),
            borderPadding=8,
            spaceAfter=10
        )
        
        story = []
        
        # Header profesional con logo simulado
        story.append(Spacer(1, 20))
        
        # Título principal con diseño profesional
        story.append(Paragraph("CLÍNICA VETERINARIA MEDIPET", header_style))
        story.append(Paragraph("HISTORIA CLÍNICA VETERINARIA", header_style))
        
        # Línea decorativa
        story.append(Spacer(1, 10))
        story.append(Paragraph("═" * 80, ParagraphStyle('DecorativeLine', 
                      parent=styles['Normal'], fontSize=12, 
                      textColor=colors.HexColor('#3b82f6'), alignment=1)))
        story.append(Spacer(1, 20))
        
        # Información del documento en formato profesional
        fecha_actual = datetime.now().strftime('%d de %B de %Y')
        doc_info = f"<b>Documento generado:</b> {fecha_actual} | <b>Historia Clínica N°:</b> {historia['Idhistoria']}"
        story.append(Paragraph(doc_info, normal_text_style))
        story.append(Spacer(1, 20))
        
        # SECCIÓN 1: INFORMACIÓN DEL PACIENTE
        story.append(Paragraph("1. INFORMACIÓN DEL PACIENTE", section_title_style))
        
        # Información de la mascota en formato de párrafos
        story.append(Paragraph("<b>Nombre de la Mascota:</b> " + (historia['nombre_mascota'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Código de Identificación:</b> " + (historia['codigo_mascota'] or 'N/A'), normal_text_style))        
        story.append(Paragraph("<b>Raza:</b> " + (historia['raza'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Sexo:</b> " + (historia['sexo'] or 'N/A'), normal_text_style))
        
        edad_texto = f"{historia['edad_años']} años, {historia['edad_meses']} meses" if historia['edad_años'] else 'N/A'
        story.append(Paragraph("<b>Edad:</b> " + edad_texto, normal_text_style))
        
        fecha_nac_texto = historia['fecha_nac'].strftime('%d/%m/%Y') if historia.get('fecha_nac') else 'N/A'
        story.append(Paragraph("<b>Fecha de Nacimiento:</b> " + fecha_nac_texto, normal_text_style))
        
        story.append(Spacer(1, 15))
        
        # SECCIÓN 2: INFORMACIÓN DEL PROPIETARIO
        story.append(Paragraph("2. INFORMACIÓN DEL PROPIETARIO", section_title_style))
        
        story.append(Paragraph("<b>Nombre Completo:</b> " + (historia['nombre_propietario'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Teléfono de Contacto:</b> " + (historia['telefono_propietario'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Correo Electrónico:</b> " + (historia['correo_propietario'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Dirección:</b> " + (historia['direccion_propietario'] or 'N/A'), normal_text_style))
        
        story.append(Spacer(1, 15))
        
        # SECCIÓN 3: INFORMACIÓN CLÍNICA INICIAL
        story.append(Paragraph("3. INFORMACIÓN CLÍNICA INICIAL", section_title_style))
        
        fecha_apertura_texto = historia['fecha_apertura'].strftime('%d/%m/%Y') if historia['fecha_apertura'] else 'N/A'
        story.append(Paragraph("<b>Fecha de Apertura:</b> " + fecha_apertura_texto, normal_text_style))
        story.append(Paragraph("<b>Veterinario Responsable:</b> " + (historia['veterinario_responsable'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Motivo de Apertura:</b> " + (historia['motivo_apertura'] or 'N/A'), normal_text_style))
        
        story.append(Spacer(1, 20))
        
        # Consultas y otros datos (versión simplificada para el ejemplo)
        if consultas:
            story.append(Paragraph("4. HISTORIAL DE CONSULTAS", section_title_style))
            for i, consulta in enumerate(consultas, 1):
                # Nueva página para cada consulta si no es la primera
                if i > 1:
                    story.append(PageBreak())
                
                fecha_str = consulta['fecha_consulta'].strftime('%d/%m/%Y')
                consulta_header = f"CONSULTA VETERINARIA #{i}"
                story.append(Paragraph(consulta_header, subsection_style))
                story.append(Paragraph(f"Fecha: {fecha_str}", normal_text_style))
                
                story.append(Paragraph(f"<b>Motivo:</b> {consulta['motivo_consulta'] or 'No especificado'}", normal_text_style))
                if consulta.get('diagnostico_definitivo'):
                    story.append(Paragraph(f"<b>Diagnóstico:</b> {consulta['diagnostico_definitivo']}", normal_text_style))
                
                # Si hay medicamentos específicos para esta consulta, mostrarlos
                if 'medicamentos_consulta' in consulta and consulta['medicamentos_consulta']:
                    story.append(Paragraph("<b>Medicamentos:</b>", normal_text_style))
                    for med in consulta['medicamentos_consulta']:
                        story.append(Paragraph(f"- {med.get('nombre_medicamento', 'No especificado')}", normal_text_style))
                
                story.append(Spacer(1, 10))
        
        # Construir PDF
        doc.build(story)
        
        # Crear nombre de archivo seguro (sin espacios ni caracteres especiales)
        import re
        nombre_mascota_seguro = re.sub(r'[^a-zA-Z0-9_-]', '_', historia["nombre_mascota"] or "mascota")
        nombre_archivo = f'historia_clinica_{nombre_mascota_seguro}_{historia["Idhistoria"]}.pdf'
        
        # Enviar correo con PDF adjunto
        from flask_mail import Message
        from app import mail
        
        try:
            # Crear mensaje de correo con PDF adjunto
            msg = Message(
                f'Historia Clínica de {historia["nombre_mascota"]}',
                recipients=[historia['correo_propietario']]
            )
            msg.body = f"""
            Estimado/a {historia['nombre_propietario']}:
            
            Adjunto encontrará la historia clínica completa de {historia['nombre_mascota']}.
            
            Saludos cordiales,
            Equipo de MediPet
            """
            
            # Adjuntar el PDF
            buffer.seek(0)
            msg.attach(
                filename=nombre_archivo,
                content_type='application/pdf',
                data=buffer.getvalue()
            )
            
            # Enviar correo
            mail.send(msg)
            
            flash(f'Historia clínica enviada exitosamente al correo {historia["correo_propietario"]}.', 'success')
        except Exception as e:
            # Registrar el error en caso de que falle el envío
            print(f"Error al enviar correo: {e}")
            flash('Error al enviar el correo electrónico. Por favor, inténtelo nuevamente.', 'error')
        
        return redirect(url_for('ver_historia_clinica', id=id))
            
    except mysql.connector.Error as err:
        flash(f'Error de base de datos: {err}', 'error')
        return redirect(url_for('ver_historia_clinica', id=id))
    finally:
        if 'cursor' in locals():
            cursor.close()
        if conn:
            conn.close()


@app.route('/historia-clinica/<int:id>')
def ver_historia_clinica(id):
    """Ver historia clínica completa de una mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_historias_clinicas'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Información básica de la historia clínica
        cursor.execute("""
            SELECT 
                hc.*,
                m.nombre as nombre_mascota,
                m.codigo as codigo_mascota,
                m.sexo,
                m.fecha_nac,
                TIMESTAMPDIFF(YEAR, m.fecha_nac, CURDATE()) as edad_años,
                TIMESTAMPDIFF(MONTH, m.fecha_nac, CURDATE()) % 12 as edad_meses,
                r.nombre as raza,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario,
                p.correo as correo_propietario,
                p.tele as telefono_propietario,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_responsable
            FROM historia_clinica hc
            JOIN mascota m ON hc.idmascota = m.Idmascota
            JOIN raza r ON m.idraza = r.Idraza
            JOIN persona p ON m.idduenio = p.Idpersona
            LEFT JOIN Usuario u ON hc.veterinario_responsable = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE hc.Idhistoria = %s
        """, (id,))
        historia = cursor.fetchone()
        
        if not historia:
            flash('Historia clínica no encontrada.', 'error')
            return redirect(url_for('gestion_historias_clinicas'))
        
        # Consultas asociadas
        cursor.execute("""
            SELECT 
                c.*,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_consulta
            FROM consulta c
            LEFT JOIN Usuario u ON c.veterinario_consulta = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE c.idhistoria = %s AND c.estado = TRUE
            ORDER BY c.fecha_consulta DESC, c.Idconsulta DESC
        """, (id,))
        consultas = cursor.fetchall()
        
        # Vacunaciones
        cursor.execute("""
            SELECT 
                vh.*,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_aplicador
            FROM vacunacion_historia vh
            LEFT JOIN Usuario u ON vh.veterinario_aplicador = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE vh.idhistoria = %s AND vh.estado = TRUE
            ORDER BY vh.fecha_aplicacion DESC
        """, (id,))
        vacunas = cursor.fetchall()
        
        return render_template('ver_historia_clinica.html', 
                             historia=historia, 
                             consultas=consultas, 
                             vacunas=vacunas)
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar historia clínica: {err}', 'error')
        return redirect(url_for('gestion_historias_clinicas'))
    finally:
        cursor.close()
        conn.close()


@app.route('/historia-clinica/<int:id>/pdf')
def historia_clinica_pdf(id):
    """Generar PDF de la historia clínica completa"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_historias_clinicas'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Información básica de la historia clínica
        cursor.execute("""
            SELECT 
                hc.*,
                m.Idmascota as idmascota,
                m.nombre as nombre_mascota,
                m.codigo as codigo_mascota,
                m.sexo,
                m.fecha_nac,
                TIMESTAMPDIFF(YEAR, m.fecha_nac, CURDATE()) as edad_años,
                TIMESTAMPDIFF(MONTH, m.fecha_nac, CURDATE()) % 12 as edad_meses,
                r.nombre as raza,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario,
                p.correo as correo_propietario,
                p.tele as telefono_propietario,
                p.direccion as direccion_propietario,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_responsable
            FROM historia_clinica hc
            JOIN mascota m ON hc.idmascota = m.Idmascota
            JOIN raza r ON m.idraza = r.Idraza
            JOIN persona p ON m.idduenio = p.Idpersona
            LEFT JOIN Usuario u ON hc.veterinario_responsable = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE hc.Idhistoria = %s
        """, (id,))
        historia = cursor.fetchone()
        
        if not historia:
            flash('Historia clínica no encontrada.', 'error')
            return redirect(url_for('gestion_historias_clinicas'))
        
        # Consultas asociadas
        cursor.execute("""
            SELECT 
                c.*,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_consulta
            FROM consulta c
            LEFT JOIN Usuario u ON c.veterinario_consulta = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE c.idhistoria = %s AND c.estado = TRUE
            ORDER BY c.fecha_consulta DESC, c.Idconsulta DESC
        """, (id,))
        consultas = cursor.fetchall()
        
        # Para cada consulta, obtener datos adicionales detallados
        for consulta in consultas:
            # Procedimientos de esta mascota (ya que no están directamente relacionados con consultas)
            cursor.execute("""
                SELECT 
                    pm.*,
                    tp.nombre as nombre_procedimiento,
                    CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_nombre
                FROM procedimientomascota pm
                JOIN tipoprocedimiento tp ON pm.idprocedimiento = tp.Idprocedimiento
                LEFT JOIN persona vet ON pm.idveterinario = vet.Idpersona
                WHERE pm.idmascota = %s AND pm.estado = TRUE
                AND pm.fecha BETWEEN DATE_SUB(%s, INTERVAL 30 DAY) AND DATE_ADD(%s, INTERVAL 1 DAY)
                ORDER BY pm.fecha DESC
            """, (historia['idmascota'], consulta['fecha_consulta'], consulta['fecha_consulta']))
            consulta['procedimientos'] = cursor.fetchall()
            
            # Medicamentos prescritos en esta consulta específica
            cursor.execute("""
                SELECT 
                    mp.*,
                    med.nombre as nombre_medicamento
                FROM medicamento_prescrito mp
                JOIN medicamento med ON mp.idmedicamento = med.Idmedicamento
                WHERE mp.idconsulta = %s
                ORDER BY mp.fecha_inicio DESC
            """, (consulta['Idconsulta'],))
            consulta['medicamentos_consulta'] = cursor.fetchall()
            
            # Enfermedades diagnosticadas en esta consulta
            cursor.execute("""
                SELECT 
                    ed.*,
                    te.nombre as nombre_enfermedad
                FROM enfermedad_diagnosticada ed
                JOIN tipoenfermedad te ON ed.idenfermedad = te.Idenfermedad
                WHERE ed.idconsulta = %s
                ORDER BY ed.fecha_diagnostico DESC
            """, (consulta['Idconsulta'],))
            consulta['enfermedades_consulta'] = cursor.fetchall()
        
        # Medicamentos prescritos (historial general)
        cursor.execute("""
            SELECT 
                mp.*,
                med.nombre as nombre_medicamento,
                c.fecha_consulta
            FROM medicamento_prescrito mp
            JOIN medicamento med ON mp.idmedicamento = med.Idmedicamento
            JOIN consulta c ON mp.idconsulta = c.Idconsulta
            WHERE c.idhistoria = %s
            ORDER BY c.fecha_consulta DESC, mp.fecha_inicio DESC
        """, (id,))
        medicamentos = cursor.fetchall()
        
        # Vacunaciones
        cursor.execute("""
            SELECT 
                vh.*,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_aplicador
            FROM vacunacion_historia vh
            LEFT JOIN Usuario u ON vh.veterinario_aplicador = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE vh.idhistoria = %s AND vh.estado = TRUE
            ORDER BY vh.fecha_aplicacion DESC
        """, (id,))
        vacunas = cursor.fetchall()
        
        # Enfermedades diagnosticadas
        cursor.execute("""
            SELECT 
                ed.*,
                te.nombre as nombre_enfermedad,
                c.fecha_consulta
            FROM enfermedad_diagnosticada ed
            JOIN tipoenfermedad te ON ed.idenfermedad = te.Idenfermedad
            JOIN consulta c ON ed.idconsulta = c.Idconsulta
            WHERE c.idhistoria = %s
            ORDER BY c.fecha_consulta DESC, ed.fecha_diagnostico DESC
        """, (id,))
        enfermedades = cursor.fetchall()
        
        # Generar PDF con diseño profesional
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=50, leftMargin=50,
                              topMargin=50, bottomMargin=50)
        
        # Estilos mejorados con diseño profesional
        styles = getSampleStyleSheet()
        
        # Estilo para el header principal
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Normal'],
            fontSize=20,
            textColor=colors.HexColor('#1e3a8a'),
            fontName='Helvetica-Bold',
            alignment=1,  # Centrado
            spaceAfter=10
        )
        
        # Estilo para subtítulos principales
        section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1f2937'),
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=colors.HexColor('#3b82f6'),
            borderPadding=5,
            backColor=colors.HexColor('#f0f9ff'),
            leftIndent=10,
            spaceAfter=15,
            spaceBefore=20
        )
        
        # Estilo para subsecciones
        subsection_style = ParagraphStyle(
            'SubsectionStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#374151'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
            spaceBefore=10
        )
        
        # Estilo para texto normal
        normal_text_style = ParagraphStyle(
            'NormalText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4b5563'),
            spaceAfter=6,
            alignment=4  # Justificado
        )
        
        # Estilo para información destacada
        highlight_style = ParagraphStyle(
            'HighlightStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor("#131414"),
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#ecfdf5'),
            borderWidth=1,
            borderColor=colors.HexColor('#10b981'),
            borderPadding=8,
            spaceAfter=10
        )
        
        story = []
        
        # Header profesional con logo simulado
        story.append(Spacer(1, 20))
        
        # Título principal con diseño profesional
        story.append(Paragraph("CLÍNICA VETERINARIA MEDIPET", header_style))
        story.append(Paragraph("HISTORIA CLÍNICA VETERINARIA", header_style))
        
        # Línea decorativa
        story.append(Spacer(1, 10))
        story.append(Paragraph("═" * 80, ParagraphStyle('DecorativeLine', 
                      parent=styles['Normal'], fontSize=12, 
                      textColor=colors.HexColor('#3b82f6'), alignment=1)))
        story.append(Spacer(1, 20))
        
        # Información del documento en formato profesional
        fecha_actual = datetime.now().strftime('%d de %B de %Y')
        doc_info = f"<b>Documento generado:</b> {fecha_actual} | <b>Historia Clínica N°:</b> {historia['Idhistoria']}"
        story.append(Paragraph(doc_info, normal_text_style))
        story.append(Spacer(1, 20))
        
        # SECCIÓN 1: INFORMACIÓN DEL PACIENTE
        story.append(Paragraph("1. INFORMACIÓN DEL PACIENTE", section_title_style))
        
        # Información de la mascota en formato de párrafos
        story.append(Paragraph("<b>Nombre de la Mascota:</b> " + (historia['nombre_mascota'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Código de Identificación:</b> " + (historia['codigo_mascota'] or 'N/A'), normal_text_style))        
        story.append(Paragraph("<b>Raza:</b> " + (historia['raza'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Sexo:</b> " + (historia['sexo'] or 'N/A'), normal_text_style))
        
        edad_texto = f"{historia['edad_años']} años, {historia['edad_meses']} meses" if historia['edad_años'] else 'N/A'
        story.append(Paragraph("<b>Edad:</b> " + edad_texto, normal_text_style))
        
        fecha_nac_texto = historia['fecha_nac'].strftime('%d/%m/%Y') if historia.get('fecha_nac') else 'N/A'
        story.append(Paragraph("<b>Fecha de Nacimiento:</b> " + fecha_nac_texto, normal_text_style))

        story.append(Spacer(1, 15))
        
        # SECCIÓN 2: INFORMACIÓN DEL PROPIETARIO
        story.append(Paragraph("2. INFORMACIÓN DEL PROPIETARIO", section_title_style))
        
        story.append(Paragraph("<b>Nombre Completo:</b> " + (historia['nombre_propietario'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Teléfono de Contacto:</b> " + (historia['telefono_propietario'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Correo Electrónico:</b> " + (historia['correo_propietario'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Dirección:</b> " + (historia['direccion_propietario'] or 'N/A'), normal_text_style))
        
        story.append(Spacer(1, 15))
        
        # SECCIÓN 3: INFORMACIÓN CLÍNICA INICIAL
        story.append(Paragraph("3. INFORMACIÓN CLÍNICA INICIAL", section_title_style))
        
        fecha_apertura_texto = historia['fecha_apertura'].strftime('%d/%m/%Y') if historia['fecha_apertura'] else 'N/A'
        story.append(Paragraph("<b>Fecha de Apertura:</b> " + fecha_apertura_texto, normal_text_style))
        story.append(Paragraph("<b>Veterinario Responsable:</b> " + (historia['veterinario_responsable'] or 'N/A'), normal_text_style))
        story.append(Paragraph("<b>Motivo de Apertura:</b> " + (historia['motivo_apertura'] or 'N/A'), normal_text_style))
        
        story.append(Spacer(1, 20))
        
        # Observaciones generales si existen
        if historia.get('observaciones_generales'):
            story.append(Paragraph("OBSERVACIONES GENERALES", subsection_style))
            obs_style = ParagraphStyle('ObservacionStyle', 
                                     fontName='Helvetica', fontSize=9, 
                                     alignment=TA_JUSTIFY, spaceAfter=10,
                                     leftIndent=10, rightIndent=10)
            story.append(Paragraph(historia['observaciones_generales'], obs_style))
        
        if historia.get('alergias_conocidas'):
            story.append(Paragraph("⚠️ ALERGIAS CONOCIDAS", subsection_style))
            alergia_style = ParagraphStyle('AlertStyle', 
                                         fontName='Helvetica-Bold', fontSize=9,
                                         alignment=TA_JUSTIFY, spaceAfter=10,
                                         backColor=colors.HexColor('#f1f5f9'), # Gris muy claro
                                         borderColor=colors.HexColor('#64748b'), # Gris neutro
                                         borderWidth=1, leftIndent=10, rightIndent=10,
                                         topPadding=6, bottomPadding=6)
            story.append(Paragraph(historia['alergias_conocidas'], alergia_style))
        
        story.append(Spacer(1, 20))
        
        # SECCIÓN 4: HISTORIAL DE CONSULTAS DETALLADO
        if consultas:
            story.append(Paragraph("4. HISTORIAL DE CONSULTAS VETERINARIAS", section_title_style))
            
            for i, consulta in enumerate(consultas):
                # Nueva página para cada consulta si no es la primera
                if i > 0:
                    story.append(PageBreak())
                
                # Header de la consulta con diseño profesional
                fecha_str = consulta['fecha_consulta'].strftime('%d/%m/%Y')
                hora_str = f" a las {consulta['hora_consulta']}" if consulta.get('hora_consulta') else ""
                
                consulta_header = f"CONSULTA VETERINARIA #{i+1}"
                story.append(Paragraph(consulta_header, subsection_style))
                story.append(Paragraph(f"Fecha: {fecha_str}{hora_str}", normal_text_style))
                story.append(Spacer(1, 10))
                
                # 4.1 Información básica de la consulta en formato de párrafos
                story.append(Paragraph("INFORMACIÓN DE LA CONSULTA", subsection_style))
                
                story.append(Paragraph(f"<b>Motivo de Consulta:</b> {consulta.get('motivo_consulta') or 'No especificado'}", normal_text_style))
                story.append(Paragraph(f"<b>Veterinario Tratante:</b> {consulta.get('veterinario_consulta') or 'No especificado'}", normal_text_style))
                story.append(Paragraph(f"<b>Estado de la Consulta:</b> {consulta.get('estado_consulta') or 'Completada'}", normal_text_style))
                
                if consulta.get('anamnesis'):
                    story.append(Paragraph(f"<b>Anamnesis:</b> {consulta['anamnesis']}", normal_text_style))
                
                story.append(Spacer(1, 15))
                
                # 4.2 Signos vitales en formato de párrafos
                if any([consulta.get('temperatura'), consulta.get('frecuencia_cardiaca'), 
                       consulta.get('frecuencia_respiratoria'), consulta.get('peso')]):
                    
                    story.append(Paragraph("SIGNOS VITALES", subsection_style))
                    
                    if consulta.get('temperatura'):
                        story.append(Paragraph(f"<b>Temperatura:</b> {consulta['temperatura']}°C", normal_text_style))
                    
                    if consulta.get('frecuencia_cardiaca'):
                        story.append(Paragraph(f"<b>Frecuencia Cardíaca:</b> {consulta['frecuencia_cardiaca']} lpm", normal_text_style))
                    
                    if consulta.get('frecuencia_respiratoria'):
                        story.append(Paragraph(f"<b>Frecuencia Respiratoria:</b> {consulta['frecuencia_respiratoria']} rpm", normal_text_style))

                    if consulta.get('peso'):
                        story.append(Paragraph(f"<b>Peso:</b> {consulta['peso']} kg", normal_text_style))

                    story.append(Spacer(1, 15))
                
                # 4.3 Examen físico por sistemas
                if any([consulta.get('examen_general'), consulta.get('sistema_cardiovascular'),
                       consulta.get('sistema_respiratorio'), consulta.get('sistema_digestivo'),
                       consulta.get('sistema_neurologico'), consulta.get('sistema_musculoesqueletico'),
                       consulta.get('piel_anexos'), consulta.get('ojos_oidos_boca')]):
                    
                    story.append(Paragraph("EXAMEN FÍSICO POR SISTEMAS", subsection_style))
                    
                    sistemas = [
                        ('Examen General', consulta.get('examen_general')),
                        ('Sistema Cardiovascular', consulta.get('sistema_cardiovascular')),
                        ('Sistema Respiratorio', consulta.get('sistema_respiratorio')),
                        ('Sistema Digestivo', consulta.get('sistema_digestivo')),
                        ('Sistema Neurológico', consulta.get('sistema_neurologico')),
                        ('Sistema Musculoesquelético', consulta.get('sistema_musculoesqueletico')),
                        ('Piel y Anexos', consulta.get('piel_anexos')),
                        ('Ojos, Oídos y Boca', consulta.get('ojos_oidos_boca'))
                    ]
                    
                    for sistema, hallazgo in sistemas:
                        if hallazgo:
                            story.append(Paragraph(f"<b>{sistema}:</b> {hallazgo}", normal_text_style))
                    
                    story.append(Spacer(1, 15))
                
                # 4.4 Diagnóstico y tratamiento
                if any([consulta.get('diagnostico_diferencial'), consulta.get('diagnostico_definitivo'),
                       consulta.get('plan_terapeutico'), consulta.get('observaciones')]):
                    
                    story.append(Paragraph("DIAGNÓSTICO Y PLAN TERAPÉUTICO", subsection_style))
                    
                    if consulta.get('diagnostico_diferencial'):
                        story.append(Paragraph(f"<b>Diagnóstico Diferencial:</b> {consulta['diagnostico_diferencial']}", normal_text_style))
                    
                    if consulta.get('diagnostico_definitivo'):
                        story.append(Paragraph(f"<b>Diagnóstico Definitivo:</b> {consulta['diagnostico_definitivo']}", normal_text_style))
                    
                    if consulta.get('plan_terapeutico'):
                        story.append(Paragraph(f"<b>Plan Terapéutico:</b> {consulta['plan_terapeutico']}", normal_text_style))
                    
                    if consulta.get('observaciones'):
                        story.append(Paragraph(f"<b>Observaciones:</b> {consulta['observaciones']}", normal_text_style))
                    
                    if consulta.get('proxima_cita'):
                        proxima_cita_str = consulta['proxima_cita'].strftime('%d/%m/%Y') if consulta['proxima_cita'] else 'No programada'
                        story.append(Paragraph(f"<b>Próxima Cita Programada:</b> {proxima_cita_str}", normal_text_style))
                    
                    story.append(Spacer(1, 20))
                
                # Si hay medicamentos específicos para esta consulta, mostrarlos
                if 'medicamentos_consulta' in consulta and consulta['medicamentos_consulta']:
                    story.append(Paragraph("MEDICAMENTOS PRESCRITOS EN ESTA CONSULTA", subsection_style))
                    
                    for j, med in enumerate(consulta['medicamentos_consulta'], 1):
                        story.append(Paragraph(f"<b>Medicamento #{j}:</b> {med.get('nombre_medicamento', 'No especificado')}", normal_text_style))
                        if med.get('dosis'):
                            story.append(Paragraph(f"<b>Dosis:</b> {med['dosis']}", normal_text_style))
                        if med.get('frecuencia'):
                            story.append(Paragraph(f"<b>Frecuencia:</b> {med['frecuencia']}", normal_text_style))
                        if med.get('duracion'):
                            story.append(Paragraph(f"<b>Duración:</b> {med['duracion']}", normal_text_style))
                        
                        story.append(Spacer(1, 10))
                    
                    story.append(Spacer(1, 15))
        
        # SECCIÓN 5: RESUMEN DE TRATAMIENTOS Y MEDICAMENTOS
        if medicamentos or vacunas:
            story.append(PageBreak())
            story.append(Paragraph("5. RESUMEN DE TRATAMIENTOS", section_title_style))
        
        # Vacunaciones en formato de párrafos
        if vacunas:
            story.append(Paragraph("HISTORIAL DE VACUNACIÓN", subsection_style))
            
            for i, vacuna in enumerate(vacunas, 1):
                story.append(Paragraph(f"<b>Vacunación #{i}</b>", highlight_style))
                
                fecha_aplicacion = vacuna['fecha_aplicacion'].strftime('%d/%m/%Y') if vacuna['fecha_aplicacion'] else 'N/A'
                story.append(Paragraph(f"<b>Fecha:</b> {fecha_aplicacion}", highlight_style))
                
                story.append(Paragraph(f"<b>Vacuna Aplicada:</b> {vacuna['nombre_vacuna'] or 'N/A'}", highlight_style))
                
                story.append(Paragraph(f"<b>Lote:</b> {vacuna['lote'] or 'N/A'}", highlight_style))
                
                proxima_dosis = vacuna['proxima_dosis'].strftime('%d/%m/%Y') if vacuna['proxima_dosis'] else 'N/A'
                story.append(Paragraph(f"<b>Próxima Dosis:</b> {proxima_dosis}", highlight_style))
                
                story.append(Paragraph(f"<b>Veterinario:</b> {vacuna['veterinario_aplicador'] or 'N/A'}", highlight_style))
                
                story.append(Spacer(1, 10))
            
            story.append(Spacer(1, 20))
        
        # Medicamentos en formato de párrafos
        if medicamentos:
            story.append(Paragraph("HISTORIAL DE MEDICAMENTOS PRESCRITOS", subsection_style))
            
            for i, med in enumerate(medicamentos, 1):
                story.append(Paragraph(f"<b>Medicamento #{i}</b>", highlight_style))
                
                fecha_consulta = med['fecha_consulta'].strftime('%d/%m/%Y') if med['fecha_consulta'] else 'N/A'
                story.append(Paragraph(f"<b>Fecha:</b> {fecha_consulta}", highlight_style))
                
                story.append(Paragraph(f"<b>Medicamento:</b> {med['nombre_medicamento'] or 'N/A'}", highlight_style))
                
                story.append(Paragraph(f"<b>Dosis:</b> {med['dosis'] or 'N/A'}", highlight_style))
                
                story.append(Paragraph(f"<b>Frecuencia:</b> {med['frecuencia'] or 'N/A'}", highlight_style))
                
                story.append(Paragraph(f"<b>Duración:</b> {med['duracion'] or 'N/A'}", highlight_style))
                
                story.append(Spacer(1, 10))
            
            story.append(Spacer(1, 20))
        
        # Enfermedades diagnosticadas
        if enfermedades:
            story.append(Paragraph("REGISTRO DE ENFERMEDADES DIAGNOSTICADAS", subsection_style))
            
            enf_data = [['FECHA', 'ENFERMEDAD', 'GRAVEDAD', 'ESTADO ACTUAL']]
            for enf in enfermedades:
                enf_data.append([
                    enf['fecha_consulta'].strftime('%d/%m/%Y') if enf['fecha_consulta'] else 'N/A',
                    enf['nombre_enfermedad'] or 'N/A',
                    enf['gravedad'] or 'N/A',
                    enf['estado_enfermedad'] or 'N/A'
                ])
            
            enf_table = Table(enf_data, colWidths=[1.2*inch, 2.5*inch, 1.2*inch, 1.1*inch])
            enf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef2f2')]),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            story.append(enf_table)
            story.append(Spacer(1, 30))
        
        # Pie de página profesional
        story.append(Spacer(1, 40))
        story.append(Paragraph("═" * 80, ParagraphStyle('DecorativeLine', 
                      parent=styles['Normal'], fontSize=8, 
                      textColor=colors.HexColor('#6b7280'), alignment=1)))
        
        footer_info = [
            f"<b>Documento generado:</b> {datetime.now().strftime('%d de %B de %Y a las %H:%M')}",
            f"<b>Clínica Veterinaria MediPet</b> - Sistema de Gestión Veterinaria",
            f"<b>Historia Clínica N°:</b> {historia['Idhistoria']} | <b>Paciente:</b> {historia['nombre_mascota']}"
        ]
        
        for info in footer_info:
            story.append(Paragraph(info, ParagraphStyle('Footer', 
                         parent=styles['Normal'], fontSize=8, 
                         textColor=colors.HexColor('#6b7280'), 
                         alignment=1, spaceAfter=3)))
        
        # Construir PDF
        doc.build(story)
        
        # Crear nombre de archivo seguro (sin espacios ni caracteres especiales)
        import re
        
        nombre_mascota_seguro = re.sub(r'[^a-zA-Z0-9_-]', '_', historia["nombre_mascota"] or "mascota")
        nombre_archivo = f'historia_clinica_{nombre_mascota_seguro}_{historia["Idhistoria"]}.pdf'
        
        # Preparar respuesta HTTP con el PDF
        buffer.seek(0)
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        
        return response
        
    except mysql.connector.Error as err:
        flash(f'Error al generar PDF: {err}', 'error')
        return redirect(url_for('ver_historia_clinica', id=id))
    finally:
        cursor.close()
        conn.close()


@app.route('/consulta/crear/<int:historia_id>', methods=['GET', 'POST'])
def crear_consulta(historia_id):
    """Crear nueva consulta en historia clínica"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('ver_historia_clinica', id=historia_id))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Datos de la consulta
        fecha_consulta = request.form.get('fecha_consulta')
        hora_consulta = request.form.get('hora_consulta')
        motivo_consulta = request.form.get('motivo_consulta', '').strip()
        anamnesis = request.form.get('anamnesis', '').strip()
        
        # Signos vitales
        temperatura = request.form.get('temperatura') or None
        frecuencia_cardiaca = request.form.get('frecuencia_cardiaca') or None
        frecuencia_respiratoria = request.form.get('frecuencia_respiratoria') or None
        peso = request.form.get('peso') or None
        
        # Examen físico
        examen_general = request.form.get('examen_general', '').strip()
        sistema_cardiovascular = request.form.get('sistema_cardiovascular', '').strip()
        sistema_respiratorio = request.form.get('sistema_respiratorio', '').strip()
        sistema_digestivo = request.form.get('sistema_digestivo', '').strip()
        sistema_neurologico = request.form.get('sistema_neurologico', '').strip()
        sistema_musculoesqueletico = request.form.get('sistema_musculoesqueletico', '').strip()
        piel_anexos = request.form.get('piel_anexos', '').strip()
        ojos_oidos_boca = request.form.get('ojos_oidos_boca', '').strip()
        
        # Diagnósticos y tratamiento
        diagnostico_diferencial = request.form.get('diagnostico_diferencial', '').strip()
        diagnostico_definitivo = request.form.get('diagnostico_definitivo', '').strip()
        plan_terapeutico = request.form.get('plan_terapeutico', '').strip()
        observaciones = request.form.get('observaciones', '').strip()
        proxima_cita = request.form.get('proxima_cita') or None
        
        if not fecha_consulta or not motivo_consulta:
            flash('La fecha y motivo de consulta son obligatorios.', 'error')
            return redirect(url_for('crear_consulta', historia_id=historia_id))
        
        try:
            query = """
                INSERT INTO consulta (
                    idhistoria, fecha_consulta, hora_consulta, motivo_consulta, anamnesis,
                    temperatura, frecuencia_cardiaca, frecuencia_respiratoria, peso,
                    examen_general, sistema_cardiovascular, sistema_respiratorio, 
                    sistema_digestivo, sistema_neurologico, sistema_musculoesqueletico,
                    piel_anexos, ojos_oidos_boca, diagnostico_diferencial, 
                    diagnostico_definitivo, plan_terapeutico, observaciones, 
                    proxima_cita, veterinario_consulta, estado_consulta
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, %s, %s, %s, 'completada'
                )
            """
            cursor.execute(query, (
                historia_id, fecha_consulta, hora_consulta, motivo_consulta, anamnesis,
                temperatura, frecuencia_cardiaca, frecuencia_respiratoria, peso,
                examen_general, sistema_cardiovascular, sistema_respiratorio,
                sistema_digestivo, sistema_neurologico, sistema_musculoesqueletico,
                piel_anexos, ojos_oidos_boca, diagnostico_diferencial,
                diagnostico_definitivo, plan_terapeutico, observaciones,
                proxima_cita, session['user_id']
            ))
            conn.commit()
            
            flash('Consulta registrada exitosamente.', 'success')
            return redirect(url_for('ver_historia_clinica', id=historia_id))
            
        except mysql.connector.Error as err:
            flash(f'Error al registrar consulta: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    # GET: Cargar datos para el formulario
    try:
        # Obtener información de la historia clínica
        cursor.execute("""
            SELECT 
                hc.*,
                m.nombre as nombre_mascota,
                m.codigo as codigo_mascota,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario
            FROM historia_clinica hc
            JOIN mascota m ON hc.idmascota = m.Idmascota
            JOIN persona p ON m.idduenio = p.Idpersona
            WHERE hc.Idhistoria = %s
        """, (historia_id,))
        historia = cursor.fetchone()
        
        if not historia:
            flash('Historia clínica no encontrada.', 'error')
            return redirect(url_for('gestion_historias_clinicas'))
        
        return render_template('crear_consulta.html', historia=historia)
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar datos: {err}', 'error')
        return redirect(url_for('ver_historia_clinica', id=historia_id))
    finally:
        cursor.close()
        conn.close()


@app.route('/consulta/ver/<int:consulta_id>')
def ver_consulta(consulta_id):
    """Ver detalles completos de una consulta"""
    # Temporalmente comentado para pruebas
    # if 'user_id' not in session:
    #     return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_historias_clinicas'))
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Información de la consulta
        cursor.execute("""
            SELECT 
                c.*,
                hc.Idhistoria as idhistoria,
                m.nombre as nombre_mascota,
                m.codigo as codigo_mascota,
                m.sexo,
                m.fecha_nac,
                r.nombre as raza,
                CONCAT(p.nom1, ' ', p.apell1) as nombre_propietario,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_consulta
            FROM consulta c
            JOIN historia_clinica hc ON c.idhistoria = hc.Idhistoria
            JOIN mascota m ON hc.idmascota = m.Idmascota
            LEFT JOIN raza r ON m.idraza = r.Idraza
            JOIN persona p ON m.idduenio = p.Idpersona
            LEFT JOIN Usuario u ON c.veterinario_consulta = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE c.Idconsulta = %s
        """, (consulta_id,))
        consulta = cursor.fetchone()
        
        if not consulta:
            flash('Consulta no encontrada.', 'error')
            return redirect(url_for('gestion_historias_clinicas'))
        
        # Medicamentos prescritos en esta consulta
        cursor.execute("""
            SELECT 
                mp.*,
                med.nombre as nombre_medicamento,
                med.presentacion
            FROM medicamento_prescrito mp
            JOIN medicamento med ON mp.idmedicamento = med.Idmedicamento
            WHERE mp.idconsulta = %s
            ORDER BY mp.fecha_creacion DESC
        """, (consulta_id,))
        medicamentos = cursor.fetchall()
        
        # Procedimientos realizados en esta consulta
        cursor.execute("""
            SELECT 
                ph.*,
                tp.nombre as nombre_procedimiento,
                CONCAT(vet.nom1, ' ', vet.apell1) as veterinario_ejecutor
            FROM procedimiento_historia ph
            JOIN tipoprocedimiento tp ON ph.idtipo_procedimiento = tp.Idprocedimiento
            LEFT JOIN Usuario u ON ph.veterinario_ejecutor = u.Idusuario
            LEFT JOIN persona vet ON u.idpersona = vet.Idpersona
            WHERE ph.idconsulta = %s
            ORDER BY ph.fecha_procedimiento DESC
        """, (consulta_id,))
        procedimientos = cursor.fetchall()
        
        return render_template('ver_consulta.html', 
                             consulta=consulta, 
                             medicamentos=medicamentos, 
                             procedimientos=procedimientos)
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar consulta: {err}', 'error')
        return redirect(url_for('gestion_historias_clinicas'))
    finally:
        cursor.close()
        conn.close()


@app.route('/medicamento/prescribir/<int:consulta_id>', methods=['GET', 'POST'])
def prescribir_medicamento(consulta_id):
    """Prescribir medicamento en una consulta"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('ver_consulta', consulta_id=consulta_id))
    
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        idmedicamento = request.form.get('idmedicamento')
        dosis = request.form.get('dosis', '').strip()
        frecuencia = request.form.get('frecuencia', '').strip()
        duracion = request.form.get('duracion', '').strip()
        via_administracion = request.form.get('via_administracion', 'oral')
        indicaciones_especiales = request.form.get('indicaciones_especiales', '').strip()
        fecha_inicio = request.form.get('fecha_inicio') or None
        fecha_fin = request.form.get('fecha_fin') or None
        
        if not all([idmedicamento, dosis, frecuencia, duracion]):
            flash('Medicamento, dosis, frecuencia y duración son obligatorios.', 'error')
            return redirect(url_for('prescribir_medicamento', consulta_id=consulta_id))
        
        try:
            query = """
                INSERT INTO medicamento_prescrito (
                    idconsulta, idmedicamento, dosis, frecuencia, duracion,
                    via_administracion, indicaciones_especiales, fecha_inicio, fecha_fin
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                consulta_id, idmedicamento, dosis, frecuencia, duracion,
                via_administracion, indicaciones_especiales, fecha_inicio, fecha_fin
            ))
            conn.commit()
            
            flash('Medicamento prescrito exitosamente.', 'success')
            return redirect(url_for('ver_consulta', consulta_id=consulta_id))
            
        except mysql.connector.Error as err:
            flash(f'Error al prescribir medicamento: {err}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    # GET: Cargar datos para el formulario
    try:
        # Obtener medicamentos activos
        cursor.execute("""
            SELECT Idmedicamento, nombre, presentacion 
            FROM medicamento 
            WHERE estado = TRUE 
            ORDER BY nombre
        """)
        medicamentos = cursor.fetchall()
        
        # Información de la consulta
        cursor.execute("""
            SELECT c.Idconsulta, c.fecha_consulta, m.nombre as nombre_mascota
            FROM consulta c
            JOIN historia_clinica hc ON c.idhistoria = hc.Idhistoria
            JOIN mascota m ON hc.idmascota = m.Idmascota
            WHERE c.Idconsulta = %s
        """, (consulta_id,))
        consulta = cursor.fetchone()
        
        if not consulta:
            flash('Consulta no encontrada.', 'error')
            return redirect(url_for('gestion_historias_clinicas'))
        
        return render_template('prescribir_medicamento.html', 
                             medicamentos=medicamentos, 
                             consulta=consulta)
        
    except mysql.connector.Error as err:
        flash(f'Error al cargar datos: {err}', 'error')
        return redirect(url_for('ver_consulta', consulta_id=consulta_id))
    finally:
        cursor.close()
        conn.close()
