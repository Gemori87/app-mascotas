from flask import render_template, request, redirect, url_for, flash, session, current_app
import mysql.connector
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
    try:
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

        # 3. Decidir a dónde redirigir al usuario
        if not has_admins:
            # Si no había administradores, este nuevo usuario será el primero.
            # Lo redirigimos a una página especial para que cree su cuenta de admin.
            return redirect(url_for('crear_primer_admin', persona_id=new_persona_id))
        else:
            # Si ya hay administradores, mostramos el mensaje normal.
            flash('Registro exitoso. Un administrador debe crear su cuenta de usuario para poder ingresar.', 'success')
            return redirect(url_for('login'))

    except mysql.connector.Error as err:
        conn.rollback()
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
        
        cursor = conn.cursor(dictionary=True)
        try:
            # Buscamos el ID del perfil 'Administrador'
            cursor.execute("SELECT Idperfil FROM Perfil WHERE descripc = 'Administrador'")
            admin_perfil = cursor.fetchone()
            if not admin_perfil:
                flash('Error crítico: El perfil "Administrador" no existe en la base de datos.', 'error')
                return redirect(url_for('login'))

            # Creamos el usuario
            query = "INSERT INTO Usuario (nombreu, contrasena, idpersona, idperfil) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nombreu, contrasena, persona_id, admin_perfil['Idperfil']))
            conn.commit()

            flash('¡Cuenta de Administrador creada exitosamente! Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            conn.rollback()
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
        if conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT u.Idusuario, u.nombreu, p.descripc FROM Usuario u JOIN Perfil p ON u.idperfil = p.Idperfil WHERE u.nombreu = %s AND u.contrasena = %s AND u.estado = TRUE"
            cursor.execute(query, (nombreu, contrasena))
            user = cursor.fetchone()
            if user:
                session.clear()
                session['user_id'] = user['Idusuario']
                session['user_name'] = user['nombreu']
                session['user_profile'] = user['descripc']
                return redirect(url_for('menu_principal'))
            else:
                flash('Usuario o contraseña incorrectos, o el usuario está inactivo.', 'error')
        else:
            flash('Error de conexión con la base de datos.', 'error')
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
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT Idusuario FROM Usuario WHERE idpersona = %s AND estado = TRUE", (id,))
        if cursor.fetchone():
            flash('No se puede inhabilitar una persona con un usuario activo.', 'error')
        else:
            try:
                cursor.execute("UPDATE Persona SET estado = NOT estado WHERE Idpersona = %s", (id,))
                conn.commit()
                flash('Estado de la persona cambiado correctamente.', 'success')
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
    if session.get('user_profile') != 'Administrador': return redirect(url_for('login'))
    conn = get_db()
    if conn:
        try:
            cursor = conn.cursor()
            query = "INSERT INTO Usuario (nombreu, contrasena, idpersona, idperfil) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (request.form['nombreu'], request.form['contrasena'], request.form['idpersona'], request.form['idperfil']))
            conn.commit()
            flash('Usuario creado exitosamente.', 'success')
        except mysql.connector.Error as err:
            conn.rollback()
            if err.errno == 1062:
                flash('Error: El nombre de usuario o la persona ya están en uso.', 'error')
            else:
                flash(f'Error al crear el usuario: {err}', 'error')
    return redirect(url_for('gestion_usuarios'))

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

from flask import render_template, request, redirect, url_for, flash, session, current_app
import mysql.connector
from .db import get_db


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
            import secrets
            import datetime
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