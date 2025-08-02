# 🐾 App de Gestión de Mascotas

Este es un proyecto de aplicación web desarrollado con Flask y Python para la gestión de una veterinaria o refugio de mascotas. Permite administrar perfiles, personas y usuarios con una conexión a una base de datos MySQL.

## ✨ Características

- **Sistema de Login:** Autenticación de usuarios contra la base de datos.
- **Gestión de Perfiles:** CRUD completo para roles (Administrador, Cliente).
- **Gestión de Personas:** CRUD completo para los datos personales de los usuarios.
- **Gestión de Usuarios:** Creación y administración de cuentas de acceso.
- **Permisos por Roles:** Vistas y acciones restringidas solo para administradores.
- **Primer Arranque Automático:** El primer usuario que se registra se convierte automáticamente en Administrador.

## 🛠️ Tecnologías Utilizadas

- **Backend:** Python, Flask
- **Base de Datos:** MySQL
- **Frontend:** HTML, Tailwind CSS
- **Conector de BD:** `mysql-connector-python`

## 🚀 Cómo Ejecutar el Proyecto

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/TU_USUARIO/TU_REPOSITORIO.git](https://github.com/TU_USUARIO/TU_REPOSITORIO.git)
    cd TU_REPOSITORIO
    ```

2.  **Crear y activar un entorno virtual:**
    ```bash
    python -m venv venv
    # En Windows
    .\venv\Scripts\activate
    # En macOS/Linux
    source venv/bin/activate
    ```

3.  **Instalar las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configurar la base de datos:**
    - Ejecuta el script SQL que se encuentra en la sección de comentarios de `app/routes.py` o un archivo `database.sql` para crear la base de datos y las tablas en tu servidor MySQL.

5.  **Configurar la conexión:**
    - Renombra el archivo `config.py.example` a `config.py`.
    - Abre `config.py` y rellena los campos `DB_USER`, `DB_PASSWORD` y `DB_PORT` con tus credenciales de MySQL.

6.  **Ejecutar la aplicación:**
    ```bash
    flask run
    ```

7.  Abre `http://127.0.0.1:5000` en tu navegador.