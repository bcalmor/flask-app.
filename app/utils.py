import re

def validar_dni(dni):
    """Valida que el DNI tenga 8 números seguidos de una letra."""
    return re.match(r'^\d{8}[A-Za-z]$', dni)

def validar_email(email):
    """Valida que el email tenga un formato correcto."""
    return re.match(r'^[^@]+@[^@]+\.[a-zA-Z]{2,}$', email)

def validar_telefono(telefono):
    """Valida que el teléfono tenga exactamente 9 dígitos."""
    return re.match(r'^\d{9}$', telefono)

def validar_nombre(nombre):
    """Valida que el nombre solo contenga letras y espacios."""
    return re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre)

def validar_datos_registro(datos):
    """
    Valida todos los datos del formulario de registro.
    Retorna una lista de errores si hay problemas, o una lista vacía si todo es válido.
    """
    errores = []

    if not validar_dni(datos['dni']):
        errores.append('El DNI debe tener 8 números seguidos de una letra.')

    if not validar_nombre(datos['nombre']):
        errores.append('El nombre solo puede contener letras y espacios.')

    if not validar_nombre(datos['apellidos']):
        errores.append('Los apellidos solo pueden contener letras y espacios.')

    if not validar_telefono(datos['telefono']):
        errores.append('El teléfono debe contener exactamente 9 dígitos.')

    if not validar_email(datos['email']):
        errores.append('El email no tiene un formato válido.')

    if len(datos['usuario']) < 4:
        errores.append('El nombre de usuario debe tener al menos 4 caracteres.')

    if len(datos['password']) < 6:
        errores.append('La contraseña debe tener al menos 6 caracteres.')

    return errores