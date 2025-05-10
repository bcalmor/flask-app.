import os
from flask import render_template, redirect, url_for, request, Flask, flash, session, jsonify 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import json
import locale
from app.utils import validar_datos_registro  # Importar validaciones desde utils.py
from app.models import load_users, save_users, load_reservas, save_reservas  # Importar funciones de datos
from functools import wraps
from app.models import is_admin_user
from config import Config  # Importar la configuración
from app import create_app
from app.email import enviar_email  # Importar la función para enviar correos
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from app.email import enviar_email  # Usaremos la función de envío de correos
from flask_mail import Mail, Message
import locale
import sys

# Configurar consola para UTF-8 (acentos y caracteres especiales)
sys.stdout.reconfigure(encoding='utf-8')

# Configurar el locale en español
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')  # Para sistemas basados en Unix (Linux, macOS)
locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')  # Para Windows

# Crear la aplicación Flask usando el patrón factory
app = create_app()
app.config.from_object(Config)
app.debug = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# Inicializar sistema de correos
mail = Mail(app)

# Hacer que la sesión sea permanente antes de cada petición
@app.before_request
def make_session_permanent():
    session.permanent = True

# Filtro personalizado para formatear fechas
@app.template_filter('datetimeformat')
def datetimeformat(value):
    date_object = datetime.strptime(value, "%Y-%m-%d")
    return date_object.strftime("%A %d de %B de %Y").capitalize()

# Decorador para proteger rutas solo accesibles por administradores
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('usuario') or not session.get('is_admin'):
            flash('Acceso denegado. Solo administradores pueden acceder.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Registrar la función como global en Jinja2
app.jinja_env.globals['is_admin_user'] = is_admin_user

# Rutas principales y lógica de la aplicación
@app.route('/')
def home_redirect():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('usuario')
        password = request.form.get('password')
        users = load_users()

        if 'users' not in users:
            flash('Error en los datos de usuarios.', 'danger')
            return render_template('login.html')

        user = next((user for user in users['users'] if user['usuario'] == username), None)
        if user:
            if check_password_hash(user['password'], password):
                session['usuario'] = user['usuario']
                session['is_admin'] = user.get('is_admin', False)  # Guardar si es administrador
                flash('Inicio de sesión exitoso.', 'success')
                return redirect(url_for('home_redirect'))
            else:
                flash('Contraseña incorrecta.', 'danger')
        else:
            flash('Usuario no encontrado.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Obtener datos del formulario
        datos = {
            "dni": request.form['dni'],
            "nombre": request.form['nombre'],
            "apellidos": request.form['apellidos'],
            "telefono": request.form['telefono'],
            "email": request.form['email'],
            "usuario": request.form['usuario'],
            "password": request.form['password']
        }

        # Validar datos usando función consolidada en utils.py
        errores = validar_datos_registro(datos)
        if errores:
            for error in errores:
                flash(error, 'danger')
            return render_template('register.html')

        # Verificar si el usuario ya existe
        users = load_users()
        if any(user['usuario'] == datos['usuario'] for user in users['users']):
            flash('El usuario ya existe. Por favor, elige otro nombre de usuario.', 'danger')
            return render_template('register.html')

        # Guardar el nuevo usuario
        new_user = {
            "dni": datos['dni'],
            "nombre": datos['nombre'],
            "apellidos": datos['apellidos'],
            "telefono": datos['telefono'],
            "email": datos['email'],
            "usuario": datos['usuario'],
            "password": generate_password_hash(datos['password'])
        }
        users['users'].append(new_user)
        save_users(users)

        # Enviar correo de confirmación
        asunto = "Confirmación de Registro"
        destinatarios = [datos['email']]
        cuerpo = f"Hola {datos['nombre']},\n\nGracias por registrarte en nuestra plataforma."
        html = f"""
        <p>Hola <strong>{datos['nombre']}</strong>,</p>
        <p>Gracias por registrarte en nuestra plataforma.</p>
        """
        enviar_email(asunto, destinatarios, cuerpo, html)

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return render_template('register.html')
    return render_template('register.html')


@app.route('/actividades')
def actividades():
    return render_template('actividades.html')

@app.route('/mis_datos', methods=['GET', 'POST'])
def mis_datos():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para ver tus datos.', 'warning')
        return redirect(url_for('login'))

    # Cargar los datos del usuario
    users = load_users()
    usuario = next((user for user in users['users'] if user['usuario'] == session['usuario']), None)

    if not usuario:
        flash('No se encontraron datos del usuario.', 'danger')
        return redirect(url_for('home_redirect'))

    return render_template('mis_datos.html', usuario=usuario)

@app.route('/guardar_datos', methods=['POST'])
def guardar_datos():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para guardar tus datos.', 'warning')
        return redirect(url_for('login'))

    # Cargar los datos del usuario
    users = load_users()
    usuario = next((user for user in users['users'] if user['usuario'] == session['usuario']), None)

    if not usuario:
        flash('No se encontraron datos del usuario.', 'danger')
        return redirect(url_for('mis_datos'))

    # Actualizar los datos del usuario (excepto DNI y usuario)
    usuario['nombre'] = request.form['nombre']
    usuario['apellidos'] = request.form['apellidos']
    usuario['telefono'] = request.form['telefono']
    usuario['email'] = request.form['email']
    usuario['direccion'] = request.form.get('direccion', '')
    usuario['fecha_nacimiento'] = request.form.get('fecha_nacimiento', '')

    # Guardar los cambios
    save_users(users)
    flash('Tus datos han sido actualizados correctamente.', 'success')
    return redirect(url_for('mis_datos'))

def limpiar_reservas_pasadas():
    """Elimina reservas cuya fecha y hora ya han pasado."""
    reservas = load_reservas()
    ahora = datetime.now()

    reservas['reservas'] = [
        reserva for reserva in reservas['reservas']
        if datetime.strptime(f"{reserva['fecha']} {reserva['hora']}", "%Y-%m-%d %H:%M") >= ahora
    ]

    save_reservas(reservas)

@app.route('/mis_reservas')
def mis_reservas():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para ver tus reservas.', 'warning')
        return redirect(url_for('login'))

    limpiar_reservas_pasadas()  # Limpiar reservas pasadas antes de cargar
    reservas = load_reservas()
    usuario_reservas = [
        reserva for reserva in reservas['reservas']
        if reserva['usuario'] == session['usuario']
    ]

    return render_template('mis_reservas.html', reservas=usuario_reservas)

@app.route('/mis_actividades')
def mis_actividades():
    usuario = session.get('usuario')  # Obtener el usuario autenticado

    if not usuario:
        flash('Debes iniciar sesión para ver tus actividades.', 'danger')
        return redirect(url_for('login'))

    # Ruta al archivo de actividades
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')

    # Leer el archivo de actividades
    if not os.path.exists(actividades_path):
        actividades = {"actividades": []}
    else:
        with open(actividades_path, 'r') as f:
            actividades = json.load(f)

    # Filtrar las actividades en las que el usuario está inscrito
    mis_actividades = [
        actividad for actividad in actividades['actividades']
        if usuario in actividad.get('inscritos', [])
    ]

    return render_template('mis_actividades.html', actividades=mis_actividades)

@app.route('/reservar_pista')
def reservar_pista():
    return render_template('reservar_pista.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('usuario', None)  # Elimina el usuario de la sesión
    flash('Tu sesión ha sido cerrada.', 'info')
    return redirect(url_for('login'))

@app.route('/api/reservas', methods=['POST'])
def api_reservas():
    if 'usuario' not in session:
        return {"error": "Debes iniciar sesión para realizar una reserva."}, 401

    data = request.json
    reservas = load_reservas()

    # Validar si la fecha y hora son válidas
    today = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%H:%M")
    if data['fecha'] < today or (data['fecha'] == today and data['hora'] < current_time):
        return {"error": "No puedes reservar en días u horas pasadas."}, 400

    # Contar reservas existentes para la misma fecha y hora
    reservas_hora = [
        reserva for reserva in reservas['reservas']
        if reserva['fecha'] == data['fecha'] and reserva['hora'] == data['hora']
    ]

    # Verificar si hay disponibilidad (máximo 3 reservas por hora)
    if len(reservas_hora) >= 3:
        return {"error": "No hay pistas disponibles para este horario."}, 400

    # Determinar las pistas disponibles (1, 2, 3)
    pistas_ocupadas = [reserva['numero_pista'] for reserva in reservas_hora]
    pistas_disponibles = [pista for pista in [1, 2, 3] if pista not in pistas_ocupadas]

    # Asignar la primera pista disponible
    if not pistas_disponibles:
        return {"error": "No hay pistas disponibles para este horario."}, 400
    numero_pista_asignada = pistas_disponibles[0]

    # Agregar la nueva reserva
    nueva_reserva = {
        "usuario": session['usuario'],
        "fecha": data['fecha'],
        "hora": data['hora'],
        "pista": data['pista'],  # "pista2" o "pista4"
        "numero_pista": numero_pista_asignada
    }
    reservas['reservas'].append(nueva_reserva)
    save_reservas(reservas)
    

    return {"message": "Reserva guardada exitosamente.", "numero_pista": numero_pista_asignada}, 200

@app.route('/api/reservas', methods=['GET'])
def get_reservas():
    reservas = load_reservas()

    # Horas disponibles iniciales
    horas_disponibles = ["10:00", "11:00", "12:00", "13:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00"]

    # Filtrar horas ocupadas
    horas_ocupadas = []
    for hora in horas_disponibles:
        for reserva in reservas['reservas']:
            reservas_hora = [
                r for r in reservas['reservas']
                if r['hora'] == hora and r['fecha'] == reserva['fecha']
            ]
            if len(reservas_hora) >= 3:  # Marcar como ocupada si hay 3 reservas
                horas_ocupadas.append(f"{reserva['fecha']}-{hora}")

    return {
        "reservas": reservas['reservas'],
        "horas_disponibles": horas_disponibles,
        "horas_ocupadas": horas_ocupadas
    }

@app.route('/api/cancelar_reserva', methods=['POST'])
def cancelar_reserva():
    if 'usuario' not in session:
        return {"error": "Debes iniciar sesión para cancelar una reserva."}, 401

    data = request.json  # Datos enviados desde el frontend
    reservas = load_reservas()  # Cargar todas las reservas existentes

    # Normalizar los datos para evitar problemas de comparación

    
    usuario = session['usuario']
    fecha = data['fecha'].strip()  # Asegurarse de que no haya espacios
    hora = data['hora'].strip()
    numero_pista = int(data['numero_pista'])  # Convertir a entero para garantizar coincidencia

    # Buscar y eliminar la reserva
    reserva_encontrada = False
    nueva_lista_reservas = []
    for reserva in reservas['reservas']:
        if (
            reserva['usuario'] == usuario and
            reserva['fecha'] == fecha and
            reserva['hora'] == hora and
            reserva['numero_pista'] == numero_pista
        ):
            reserva_encontrada = True  # Marcar que se encontró la reserva
        else:
            nueva_lista_reservas.append(reserva)

    if not reserva_encontrada:
        return {"error": "No se encontró la reserva para cancelar."}, 404

    # Actualizar las reservas y guardar
    reservas['reservas'] = nueva_lista_reservas
    save_reservas(reservas)

    return {"message": "Reserva cancelada exitosamente."}, 200

@app.route('/api/cancelar_inscripcion', methods=['POST'])
def cancelar_inscripcion():
    if 'usuario' not in session:
        return {"error": "Debes iniciar sesión para cancelar tu inscripción."}, 401

    data = request.json  # Datos enviados desde el frontend
    torneo = data.get('torneo')  # Nombre del torneo
    usuario = session['usuario']  # Usuario autenticado

    # Ruta al archivo de actividades
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')

    # Verificar si el archivo de actividades existe
    if not os.path.exists(actividades_path):
        return {"error": "No se encontró el archivo de actividades."}, 404

    # Leer el archivo de actividades
    with open(actividades_path, 'r') as f:
        actividades = json.load(f)

    # Buscar el torneo y eliminar al usuario de la lista de inscritos
    for actividad in actividades['actividades']:
        if actividad['nombre'] == torneo:
            if 'inscritos' in actividad and usuario in actividad['inscritos']:
                actividad['inscritos'].remove(usuario)
                break
    else:
        return {"error": "No estás inscrito en este torneo o no se encontró el torneo."}, 404

    # Guardar los cambios en el archivo
    with open(actividades_path, 'w') as f:
        json.dump(actividades, f, indent=4)

    return {"message": "Tu inscripción ha sido cancelada exitosamente."}, 200

@app.route('/torneos')
def torneos():
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        actividades = {"actividades": []}
    else:
        with open(actividades_path, 'r') as f:
            actividades = json.load(f)

    return render_template('torneos.html', torneos=actividades["actividades"])

@app.route('/clases')
def clases():
    return render_template('clases.html')

@app.route('/pickleball')
def pickleball():
    return render_template('pickleball.html')

@app.route('/tiendas')
def tiendas():
    return render_template('palas_padel.html')

@app.route('/admin/torneos', methods=['GET'])
@admin_required
def admin_torneos():
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        actividades = {"actividades": []}
    else:
        with open(actividades_path, 'r') as f:
            actividades = json.load(f)

    return render_template('admin_torneos.html', torneos=actividades["actividades"])

@app.route('/admin/add_torneo', methods=['POST'])
@admin_required
def add_torneo():
    print("Usuario en sesión:", session.get('usuario'))
    print("Es administrador:", session.get('is_admin'))
    print("Datos del formulario:", request.form)

     # Obtener los premios como un string y separarlos por líneas
    premios_text = request.form['premios']
    premios = [premio.strip() for premio in premios_text.split('\n') if premio.strip()]  # Filtra líneas vacías

    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        actividades = {"actividades": []}  # Crear un diccionario con una lista vacía
    else:
        with open(actividades_path, 'r') as f:
            try:
                actividades = json.load(f)
            except json.JSONDecodeError:
                actividades = {"actividades": []}  # Si hay un error, inicializar correctamente

    # Crear el nuevo torneo con los datos del formulario
    nuevo_torneo = {
        "nombre": request.form['nombre'],
        "fecha": request.form['fecha'],
        "hora": request.form['hora'],
        "ubicacion": request.form['ubicacion'],
        "precio": request.form['precio'],
        "descripcion": request.form['descripcion'],
        "premios": request.form['premios']
    }
    actividades["actividades"].append(nuevo_torneo)  # Agregar el torneo a la lista dentro del diccionario

    # Guardar el nuevo torneo en el archivo JSON
    with open(actividades_path, 'w') as f:
        json.dump(actividades, f, indent=4)

    flash('Torneo agregado exitosamente.', 'success')
    return redirect(url_for('admin_torneos'))

@app.route('/inscribir_torneo', methods=['POST'])
def inscribir_torneo():
    data = request.get_json()
    torneo = data.get('torneo')
    usuario = session.get('usuario')  # Obtener el usuario autenticado

    if not usuario:
        return jsonify({'success': False, 'message': 'Usuario no autenticado'}), 401

    # Ruta al archivo de actividades
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')

    # Verificar si el archivo de actividades existe
    if not os.path.exists(actividades_path):
        return jsonify({'success': False, 'message': 'No se encontró el archivo de actividades.'}), 404

    # Leer el archivo de actividades
    with open(actividades_path, 'r') as f:
        actividades = json.load(f)

    # Buscar el torneo y agregar al usuario
    for actividad in actividades['actividades']:
        if actividad['nombre'] == torneo:
            if 'inscritos' not in actividad:
                actividad['inscritos'] = []
            if usuario in actividad['inscritos']:
                return jsonify({'success': False, 'message': 'Ya estás inscrito en este torneo.'}), 400
            actividad['inscritos'].append(usuario)  # Agregar al usuario a la lista de inscritos
            break
    else:
        return jsonify({'success': False, 'message': 'Torneo no encontrado.'}), 404

    # Guardar los cambios en el archivo de actividades
    try:
        with open(actividades_path, 'w') as f:
            json.dump(actividades, f, indent=4)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error al guardar los cambios: {e}'}), 500

    return jsonify({'success': True, 'message': 'Inscripción realizada con éxito'})

@app.route('/pago')
def pago():
    return render_template('pago.html')

@app.route('/enviar_email', methods=['POST'])
def enviar_email():
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    asunto = request.form.get('asunto')
    mensaje = request.form.get('mensaje')

    # Crear el mensaje que se enviará al administrador
    cuerpo = f"""
    Has recibido un nuevo mensaje desde el formulario de contacto:

    Nombre: {nombre}
    Email: {email}
    Asunto: {asunto}
    Mensaje:
    {mensaje}
    """

    # Crear el objeto Message de Flask-Mail
    msg = Message(
        asunto,
        recipients=['becalmor@gmail.com'],  # Cambia esto por el correo del administrador
        body=cuerpo
    )

    try:
        # Enviar el correo
        mail.send(msg)
        flash('Tu mensaje ha sido enviado con éxito. Nos pondremos en contacto contigo pronto.', 'success')
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        flash('Hubo un error al enviar el mensaje. Por favor, intenta nuevamente más tarde.', 'error')

    # Redirigir de nuevo a la página de contacto
    return redirect(url_for('contacto'))  # Aquí 'contacto' es la ruta que muestra el formulario

@app.route('/contacto')
def contacto():
    return render_template('contacto.html')

@app.route('/admin', methods=['GET'])
@admin_required
def admin_panel():
    # Cargar las reservas
    reservas_path = os.path.join(app.root_path, 'static', 'data', 'reservas.json')
    if not os.path.exists(reservas_path):
        reservas = []
    else:
        with open(reservas_path, 'r') as f:
            try:
                data = json.load(f)
                reservas = data.get("reservas", [])
            except (json.JSONDecodeError, ValueError) as e:
                reservas = []
                print(f"Error al cargar reservas.json: {e}")

    # Ordenar las reservas por fecha y hora
    reservas = sorted(reservas, key=lambda x: (x['fecha'], x['hora']))

    # Cargar los torneos
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        torneos = []
    else:
        with open(actividades_path, 'r') as f:
            try:
                actividades = json.load(f)
                torneos = actividades.get("actividades", [])
            except (json.JSONDecodeError, ValueError) as e:
                torneos = []
                print(f"Error al cargar actividades.json: {e}")

    return render_template('admin_panel.html', reservas=reservas, torneos=torneos)

@app.route('/admin/upload_news', methods=['POST'])
@admin_required
def upload_news():
    noticias_path = os.path.join(app.root_path, 'static', 'data', 'noticias.json')
    if not os.path.exists(noticias_path):
        noticias = []
    else:
        with open(noticias_path, 'r') as f:
            try:
                noticias = json.load(f)
            except json.JSONDecodeError:
                noticias = []

    nueva_noticia = {
        "titulo": request.form['titulo'],
        "fecha": datetime.now().strftime('%Y-%m-%d'),
        "contenido": request.form['contenido'],
        "imagen": None
    }

    if 'imagen' in request.files:
        imagen = request.files['imagen']
        if imagen.filename != '':
            # Guardar la imagen en static/images
            imagen_path = os.path.join(app.static_folder, 'images', imagen.filename)
            os.makedirs(os.path.dirname(imagen_path), exist_ok=True)
            imagen.save(imagen_path)
            nueva_noticia['imagen'] = imagen.filename

    noticias.append(nueva_noticia)

    with open(noticias_path, 'w') as f:
        json.dump(noticias, f, indent=4)

    flash('Noticia subida exitosamente.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_torneo/<nombre>', methods=['POST'])
@admin_required
def delete_torneo(nombre):
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        flash('No se encontró el archivo de actividades.', 'danger')
        return redirect(url_for('torneos'))

    with open(actividades_path, 'r') as f:
        actividades = json.load(f)

    # Filtrar los torneos para eliminar el que coincida con el nombre
    actividades["actividades"] = [torneo for torneo in actividades["actividades"] if torneo.get("nombre") != nombre]

    # Guardar los cambios
    with open(actividades_path, 'w') as f:
        json.dump(actividades, f, indent=4)

    flash(f'Torneo "{nombre}" eliminado exitosamente.', 'success')
    return redirect(url_for('torneos'))

@app.route('/admin/edit_torneo/<nombre>', methods=['GET', 'POST'])
@admin_required
def edit_torneo(nombre):
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        flash('No se encontró el archivo de actividades.', 'danger')
        return redirect(url_for('torneos'))

    with open(actividades_path, 'r') as f:
        actividades = json.load(f)

    # Buscar el torneo a modificar
    torneo = next((t for t in actividades["actividades"] if t.get("nombre") == nombre), None)
    if not torneo:
        flash(f'No se encontró el torneo "{nombre}".', 'danger')
        return redirect(url_for('torneos'))

    if request.method == 'POST':
        # Actualizar los datos del torneo con los valores del formulario
        torneo["nombre"] = request.form['nombre']
        torneo["fecha"] = request.form['fecha']
        torneo["hora"] = request.form['hora']
        torneo["ubicacion"] = request.form['ubicacion']
        torneo["precio"] = request.form['precio']
        torneo["descripcion"] = request.form['descripcion']
        torneo["premios"] = request.form['premios']

        # Guardar los cambios
        with open(actividades_path, 'w') as f:
            json.dump(actividades, f, indent=4)

        flash(f'Torneo "{nombre}" modificado exitosamente.', 'success')
        return redirect(url_for('torneos'))

    return render_template('edit_torneo.html', torneo=torneo)

@app.route('/noticias')
def noticias():
    noticias_path = os.path.join(app.root_path, 'static', 'data', 'noticias.json')
    if not os.path.exists(noticias_path):
        noticias = []
    else:
        with open(noticias_path, 'r') as f:
            noticias = json.load(f)

    # Ordenar las noticias por fecha (de más reciente a más antigua)
    noticias = sorted(noticias, key=lambda x: x['fecha'], reverse=True)

    return render_template('noticias.html', noticias=noticias)

@app.route('/admin/delete_news/<titulo>', methods=['POST'])
@admin_required
def delete_news(titulo):
    noticias_path = os.path.join(app.root_path, 'static', 'data', 'noticias.json')
    if not os.path.exists(noticias_path):
        flash('No se encontró el archivo de noticias.', 'danger')
        return redirect(url_for('noticias'))

    with open(noticias_path, 'r') as f:
        noticias = json.load(f)

    # Filtrar las noticias para eliminar la que coincida con el título
    noticias = [noticia for noticia in noticias if noticia.get("titulo") != titulo]

    # Guardar los cambios
    with open(noticias_path, 'w') as f:
        json.dump(noticias, f, indent=4)

    flash(f'Noticia "{titulo}" eliminada exitosamente.', 'success')
    return redirect(url_for('noticias'))

@app.route('/admin/reservas', methods=['GET'])
@admin_required
def admin_reservas():
    reservas_path = os.path.join(app.root_path, 'static', 'data', 'reservas.json')
    if not os.path.exists(reservas_path):
        reservas = []
    else:
        with open(reservas_path, 'r') as f:
            try:
                data = json.load(f)  # Cargar el archivo completo
                reservas = data.get("reservas", [])  # Acceder a la clave "reservas"
            except (json.JSONDecodeError, ValueError) as e:
                reservas = []
                print(f"Error al cargar reservas.json: {e}")

    # Ordenar las reservas por fecha y hora
    reservas = sorted(reservas, key=lambda x: (x['fecha'], x['hora']))

    return render_template('admin_reservas.html', reservas=reservas)

@app.route('/admin/inscritos', methods=['GET'])
@admin_required
def admin_inscritos():
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        actividades = {"actividades": []}
    else:
        with open(actividades_path, 'r') as f:
            try:
                actividades = json.load(f)
            except (json.JSONDecodeError, ValueError) as e:
                actividades = {"actividades": []}
                print(f"Error al cargar actividades.json: {e}")

    return render_template('admin_inscritos.html', torneos=actividades["actividades"])

@app.route('/clubes')
def clubes():
    # Ruta al archivo de datos de clubes
    clubes_path = os.path.join(app.root_path, 'static', 'data', 'clubes.json')

    # Verificar si el archivo existe
    if not os.path.exists(clubes_path):
        clubes = []  # Si no existe, inicializar una lista vacía
    else:
        with open(clubes_path, 'r', encoding='utf-8') as f:
            try:
                clubes = json.load(f)  # Cargar los datos de los clubes
            except json.JSONDecodeError:
                clubes = []  # Si hay un error, inicializar una lista vacía

    return render_template('clubes.html', clubes=clubes)

@app.route('/clubes/valorar/<int:club_id>', methods=['POST'])
def valorar_club(club_id):
    # Obtener la valoración enviada desde el formulario
    rating = request.form.get('rating')

    # Ruta al archivo de datos de clubes
    clubes_path = os.path.join(app.root_path, 'static', 'data', 'clubes.json')

    # Leer los datos de los clubes
    if not os.path.exists(clubes_path):
        return {"error": "No se encontró el archivo de clubes."}, 404

    with open(clubes_path, 'r', encoding='utf-8') as f:
        clubes = json.load(f)

    # Buscar el club por ID y actualizar su valoración
    for club in clubes:
        if club.get('id') == club_id:
            if 'valoraciones' not in club:
                club['valoraciones'] = []
            club['valoraciones'].append(int(rating))
            break
    else:
        return {"error": "No se encontró el club."}, 404

    # Guardar los cambios en el archivo
    with open(clubes_path, 'w', encoding='utf-8') as f:
        json.dump(clubes, f, indent=4, ensure_ascii=False)

    flash('¡Gracias por tu valoración!', 'success')
    return redirect(url_for('clubes'))

@app.route('/clubes/contactar/<int:club_id>', methods=['POST'])
def contactar_club(club_id):
    # Obtener los datos enviados desde el formulario
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    mensaje = request.form.get('mensaje')

    # Ruta al archivo de datos de clubes
    clubes_path = os.path.join(app.root_path, 'static', 'data', 'clubes.json')

    # Leer los datos de los clubes
    if not os.path.exists(clubes_path):
        return {"error": "No se encontró el archivo de clubes."}, 404

    with open(clubes_path, 'r', encoding='utf-8') as f:
        clubes = json.load(f)

    # Buscar el club por ID
    club = next((c for c in clubes if c.get('id') == club_id), None)
    if not club:
        return {"error": "No se encontró el club."}, 404

    # Simular el envío del mensaje (puedes integrarlo con un sistema de correo)
    print(f"Mensaje enviado a {club['email']} de {nombre} ({email}): {mensaje}")

    flash('Tu mensaje ha sido enviado al club.', 'success')
    return redirect(url_for('clubes'))

# Configurar el programador
scheduler = BackgroundScheduler()

def enviar_recordatorios_reservas():
    """Envía recordatorios de reservas próximas a los usuarios."""
    reservas = load_reservas()
    hoy = datetime.now()
    proximas_24_horas = hoy + timedelta(hours=24)

    for reserva in reservas['reservas']:
        fecha_reserva = datetime.strptime(reserva['fecha'] + " " + reserva['hora'], "%Y-%m-%d %H:%M")
        if hoy < fecha_reserva <= proximas_24_horas:
            # Enviar correo al usuario
            asunto = "Recordatorio de tu reserva"
            destinatarios = [buscar_email_usuario(reserva['usuario'])]
            cuerpo = f"""
            Hola {reserva['usuario']},

            Te recordamos que tienes una reserva programada:
            - Fecha: {reserva['fecha']}
            - Hora: {reserva['hora']}
            - Pista: {reserva['numero_pista']}

            ¡Te esperamos!
            """
            html = f"""
            <p>Hola <strong>{reserva['usuario']}</strong>,</p>
            <p>Te recordamos que tienes una reserva programada:</p>
            <ul>
                <li><strong>Fecha:</strong> {reserva['fecha']}</li>
                <li><strong>Hora:</strong> {reserva['hora']}</li>
                <li><strong>Pista:</strong> {reserva['numero_pista']}</li>
            </ul>
            <p>¡Te esperamos!</p>
            """
            enviar_email(asunto, destinatarios, cuerpo, html)

def enviar_recordatorios_torneos():
    """Envía recordatorios de torneos próximos a los usuarios inscritos."""
    actividades_path = os.path.join(app.root_path, 'static', 'data', 'actividades.json')
    if not os.path.exists(actividades_path):
        return

    with open(actividades_path, 'r') as f:
        actividades = json.load(f)

    hoy = datetime.now()
    proximas_24_horas = hoy + timedelta(hours=24)

    for actividad in actividades['actividades']:
        fecha_torneo = datetime.strptime(actividad['fecha'] + " " + actividad['hora'], "%Y-%m-%d %H:%M")
        if hoy < fecha_torneo <= proximas_24_horas:
            if 'inscritos' in actividad:
                for usuario in actividad['inscritos']:
                    # Enviar correo al usuario
                    asunto = "Recordatorio de tu torneo"
                    destinatarios = [buscar_email_usuario(usuario)]
                    cuerpo = f"""
                    Hola {usuario},

                    Te recordamos que estás inscrito en el torneo:
                    - Nombre: {actividad['nombre']}
                    - Fecha: {actividad['fecha']}
                    - Hora: {actividad['hora']}
                    - Ubicación: {actividad['ubicacion']}

                    ¡Te deseamos mucha suerte!
                    """
                    html = f"""
                    <p>Hola <strong>{usuario}</strong>,</p>
                    <p>Te recordamos que estás inscrito en el torneo:</p>
                    <ul>
                        <li><strong>Nombre:</strong> {actividad['nombre']}</li>
                        <li><strong>Fecha:</strong> {actividad['fecha']}</li>
                        <li><strong>Hora:</strong> {actividad['hora']}</li>
                        <li><strong>Ubicación:</strong> {actividad['ubicacion']}</li>
                    </ul>
                    <p>¡Te deseamos mucha suerte!</p>
                    """
                    enviar_email(asunto, destinatarios, cuerpo, html)

def buscar_email_usuario(usuario):
    """Busca el email de un usuario en el archivo de usuarios."""
    users = load_users()
    for user in users['users']:
        if user['usuario'] == usuario:
            return user['email']
    return None

# Añadir las tareas al programador
scheduler.add_job(enviar_recordatorios_reservas, 'interval', hours=1)  # Ejecutar cada hora
scheduler.add_job(enviar_recordatorios_torneos, 'interval', hours=1)  # Ejecutar cada hora

# Iniciar el programador
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True)

