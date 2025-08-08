from flask import render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime, timedelta
import mysql.connector
import secrets
from .db import get_db
from flask_mail import Message
from app import mail

app = current_app


@app.route('/persona/crear', methods=['POST'])
def crear_persona():
    nom1 = request.form['nom1']
    apell1 = request.form['apell1']
    correo = request.form['correo']
    if not nom1 or not apell1 or not correo:
        flash('Primer nombre, primer apellido y correo son obligatorios.', 'error')
        return redirect(url_for('gestion_personas'))

    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_personas'))

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Verificar si ya existen administradores
        cursor.execute("""
            SELECT COUNT(u.Idusuario) as admin_count
            FROM Usuario u
            JOIN Perfil p ON u.idperfil = p.Idperfil
            WHERE p.descripc = 'Administrador'
        """)
        has_admins = cursor.fetchone()['admin_count'] > 0
        
        # 2. Intentar crear la persona
        query = """
            INSERT INTO Persona (nom1, nom2, apell1, apell2, direccion, tele, movil, correo, fecha_nac)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        fecha_nac = request.form.get('fecha_nac') or None
        cursor.execute(query, (
            request.form['nom1'], request.form.get('nom2'), request.form['apell1'],
            request.form.get('apell2'), request.form.get('direccion'), request.form.get('tele'),
            request.form.get('movil'), request.form['correo'], fecha_nac
        ))
        
        new_persona_id = cursor.lastrowid # Obtenemos el ID de la persona recién creada
        conn.commit()

        cursor.close()
        conn.close()

        # 3. Decidir a dónde redirigir al usuario
        if not has_admins:
            # Si no había administradores, este nuevo usuario será el primero.
            # Lo redirigimos a una página especial para que cree su cuenta de admin.
            return redirect(url_for('crear_primer_admin', persona_id=new_persona_id))
        else:
            # Si ya hay administradores, regresamos a la gestión de personas.
            flash('Persona registrada exitosamente. Un administrador debe crear su cuenta de usuario para poder ingresar.', 'success')
            return redirect(url_for('gestion_personas'))

    except mysql.connector.Error as err:
        conn.rollback()
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if err.errno == 1062:
            flash('Error: El correo electrónico ya está registrado.', 'error')
        else:
            flash(f'Error al crear la persona: {err}', 'error')
        return redirect(url_for('gestion_personas'))



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

@app.route('/personas')
def gestion_personas():
    conn = get_db()
    personas = []
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Idpersona, nom1, apell1, correo, estado FROM Persona ORDER BY Idpersona DESC")
        personas = cursor.fetchall()
    return render_template('gestion_personas.html', personas=personas)

@app.route('/persona/editar/<int:id>', methods=['GET', 'POST'])
def editar_persona(id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    if not conn:
        flash('Error de conexión con la base de datos.', 'error')
        return redirect(url_for('gestion_personas'))
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        try:
            update_query = "UPDATE Persona SET nom1 = %s, nom2 = %s, apell1 = %s, apell2 = %s, direccion = %s, tele = %s, movil = %s, correo = %s, fecha_nac = %s WHERE Idpersona = %s"
            fecha_nac = request.form.get('fecha_nac') or None
            cursor.execute(update_query, (request.form['nom1'], request.form.get('nom2'), request.form['apell1'], request.form.get('apell2'), request.form.get('direccion'), request.form.get('tele'), request.form.get('movil'), request.form['correo'], fecha_nac, id))
            conn.commit()
            flash('Persona actualizada correctamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Error al actualizar la persona: {err}', 'error')
        return redirect(url_for('gestion_personas'))
    cursor.execute("SELECT * FROM Persona WHERE Idpersona = %s", (id,))
    persona = cursor.fetchone()
    if persona:
        return render_template('editar_persona.html', persona=persona)
    else:
        flash('Persona no encontrada.', 'error')
        return redirect(url_for('gestion_personas'))

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

@app.route('/medicamentos')
def gestion_medicamentos():
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
    return render_template('gestion_medicamentos.html', usuarios=usuarios, personas=personas, perfiles=perfiles)

@app.route('/veterinarios')
def gestion_veterinarios():
    if session.get('user_profile') != 'Administrador':
        flash('Acceso no autorizado.', 'error')
        return redirect(url_for('menu_principal'))

    conn = get_db()
    usuarios, personas, perfiles, mascotas = [], [], [], []

    if conn:
        cursor = conn.cursor(dictionary=True)


        # Usuarios veterinarios ya registrados
        query_usuarios = """
            SELECT u.Idusuario, u.nombreu, CONCAT(pe.nom1, ' ', pe.apell1) as nombre_persona,
                   pr.descripc, u.estado
            FROM Usuario u
            JOIN Persona pe ON u.idpersona = pe.Idpersona
            JOIN Perfil pr ON u.idperfil = pr.Idperfil
            ORDER BY u.Idusuario DESC
        """
        cursor.execute(query_usuarios)
        usuarios = cursor.fetchall()

        # Personas sin usuario asignado (para crear nuevos usuarios)
        cursor.execute("""
            SELECT Idpersona, CONCAT(nom1, ' ', apell1) as nombre_completo
            FROM Persona
            WHERE estado = TRUE AND Idpersona NOT IN (SELECT idpersona FROM Usuario)
        """)
        personas = cursor.fetchall()

        # Perfiles activos
        cursor.execute("SELECT Idperfil, descripc FROM Perfil WHERE estado = TRUE")
        perfiles = cursor.fetchall()

        # Mascotas activas
        cursor.execute("SELECT Idmascota, nombre FROM mascota WHERE estado = 1")
        mascotas = cursor.fetchall()

    return render_template(
        'gestion_veterinarios.html',
        usuarios=usuarios,
        personas=personas,
        perfiles=perfiles,
        mascotas=mascotas
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
                "Restablecer contraseña - App Mascotas",
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
        SELECT me.id, me.idmascota, me.idenfermedad, me.fecha, me.observacion,
               m.nombre as nombre_mascota, te.nombre as nombre_enfermedad
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
            SELECT me.*, m.nombre as nombre_mascota, m.raza, m.edad, m.peso,
                   te.nombre as nombre_enfermedad, te.observaciones as observaciones_enfermedad
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
    finally:
        cursor.close()
        conn.close()
    
    return render_template('ver_enfermedad_mascota.html', enfermedad_mascota=enfermedad_mascota)


@app.route('/enfermedad-mascota/eliminar/<int:id>')
def eliminar_enfermedad_mascota(id):
    """Eliminar registro de enfermedad de mascota"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Solo administradores pueden eliminar
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
        
        # Eliminar el registro
        cursor.execute("DELETE FROM mascotaenfermedad WHERE id = %s", (id,))
        conn.commit()
        
        flash('Registro eliminado exitosamente.', 'success')
        
    except mysql.connector.Error as err:
        flash(f'Error al eliminar registro: {err}', 'error')
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
        # Query para obtener la lista de mascotas con nombres de raza y dueño
        mascotas_query = """
            SELECT m.Idmascota, m.nombre, m.estado, r.nombre AS raza_nombre, p.nom1 AS duenio_nombre
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
        cursor.execute("SELECT Idpersona, nom1, apell1 FROM persona WHERE estado = 1 ORDER BY nom1 ASC")
        duenios = cursor.fetchall()

    return render_template('gestion_mascotas.html', mascotas=mascotas, razas=razas, duenios=duenios)

@app.route('/mascota/crear', methods=['POST'])
def crear_mascota():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO mascota (codigo, nombre, fecha_nac, caracteristicas, idraza, idduenio)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        fecha_nac = request.form.get('fecha_nac') or None
        cursor.execute(query, (
            request.form['codigo'], request.form['nombre'], fecha_nac,
            request.form.get('caracteristicas'), request.form['idraza'], request.form['idduenio']
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
            query = """
                UPDATE mascota SET
                codigo = %s, nombre = %s, fecha_nac = %s, caracteristicas = %s,
                idraza = %s, idduenio = %s
                WHERE Idmascota = %s
            """
            fecha_nac = request.form.get('fecha_nac') or None
            cursor.execute(query, (
                request.form['codigo'], request.form['nombre'], fecha_nac,
                request.form.get('caracteristicas'), request.form['idraza'], request.form['idduenio'], id
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
    
    cursor.execute("SELECT Idpersona, nom1, apell1 FROM persona WHERE estado = 1 ORDER BY nom1 ASC")
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

    conn = get_db()
    if conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE mascota SET idveterinario = %s WHERE Idmascota = %s", (idusuario, idmascota))
        conn.commit()
        flash("Mascota asignada exitosamente", "success")

    return redirect(url_for('gestion_veterinarios'))  # <- evita error de template faltante


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