import os
import json
from functools import wraps
from flask import session, flash, redirect, url_for

# Define la ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Función para cargar usuarios
def load_users():
    users_path = os.path.join(BASE_DIR, 'static', 'data', 'users.json')
    try:
        with open(users_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": []}

# Función para guardar usuarios
def save_users(users):
    users_path = os.path.join(BASE_DIR, 'static', 'data', 'users.json')
    os.makedirs(os.path.dirname(users_path), exist_ok=True)
    with open(users_path, 'w') as f:
        json.dump(users, f, indent=4)

# Función para comprobar si un usuario es administrador
def is_admin_user(username):
    """Comprueba si un usuario es administrador."""
    users = load_users()
    user = next((u for u in users['users'] if u['usuario'] == username), None)
    return user and user.get('is_admin', False)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('usuario') or not session.get('is_admin'):
            flash('Acceso denegado. Solo administradores pueden acceder.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Función para cargar reservas
def load_reservas():
    reservas_path = os.path.join(BASE_DIR, 'static', 'data', 'reservas.json')
    try:
        with open(reservas_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"reservas": []}

# Función para guardar reservas
def save_reservas(reservas):
    reservas_path = os.path.join(BASE_DIR, 'static', 'data', 'reservas.json')
    os.makedirs(os.path.dirname(reservas_path), exist_ok=True)
    with open(reservas_path, 'w') as f:
        json.dump(reservas, f, indent=4)