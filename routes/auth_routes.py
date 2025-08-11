from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection_usuarios
from auth import generar_token, verificar_token_request

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    nombre = data.get('nombre')
    appaterno = data.get('app')
    apmaterno = data.get('apm')
    correo = data.get('correo')
    password = data.get('password')
    tipo = data.get('tipo', 0)

    if not all([nombre, appaterno, correo, password]):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    hashed_password = generate_password_hash(password)

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id_user FROM users WHERE correo = %s", (correo,))
            if cursor.fetchone():
                return jsonify({'error': 'Correo ya registrado'}), 400

            query = """
                INSERT INTO users (nombre, app, apm, correo, password, tipo) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, appaterno, apmaterno, correo, hashed_password, tipo))
            db.commit()
            return jsonify({'message': 'Usuario registrado exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@auth_bp.route('/users/<int:id>', methods=['PUT'])
def actualizar_usuario(id):
    data = request.json
    nombre = data.get('nombre')
    appaterno = data.get('app')
    apmaterno = data.get('apm')
    correo = data.get('correo')
    password = data.get('password')
    tipo = data.get('tipo')

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id_user FROM users WHERE id_user = %s", (id,))
            if not cursor.fetchone():
                return jsonify({'error': 'Usuario no encontrado'}), 404

            if correo:
                cursor.execute("SELECT id_user FROM users WHERE correo = %s AND id_user != %s", (correo, id))
                if cursor.fetchone():
                    return jsonify({'error': 'Correo ya registrado'}), 400

            updates = []
            params = []
            
            if nombre:
                updates.append("nombre = %s")
                params.append(nombre)
            if appaterno:
                updates.append("app = %s")
                params.append(appaterno)
            if apmaterno:
                updates.append("apm = %s")
                params.append(apmaterno)
            if correo:
                updates.append("correo = %s")
                params.append(correo)
            if password:
                updates.append("password = %s")
                params.append(generate_password_hash(password))
            if tipo is not None:
                updates.append("tipo = %s")
                params.append(tipo)

            if not updates:
                return jsonify({'error': 'No hay datos para actualizar'}), 400

            params.append(id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id_user = %s"
            cursor.execute(query, params)
            db.commit()

            return jsonify({'message': 'Usuario actualizado exitosamente'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@auth_bp.route('/users', methods=['GET'])
def obtener_usuarios():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = "SELECT id_user, nombre, app, apm, correo, tipo FROM users"
            cursor.execute(query)
            usuarios = cursor.fetchall()
            return jsonify(usuarios), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@auth_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    correo = data.get('correo')
    password = data.get('password')

    if not correo or not password:
        return jsonify({'error': 'Correo y contraseña son requeridos'}), 400

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE correo = %s", (correo,))
            user = cursor.fetchone()
            if not user or not check_password_hash(user['password'], password):
                return jsonify({'error': 'Correo o contraseña incorrectos'}), 401

            token = generar_token(user['id_user'])

            return jsonify({
                'message': 'Login exitoso',
                'user': {
                    'id': user['id_user'],
                    'nombre': user['nombre'],
                    'correo': user['correo'],
                    'tipo': user['tipo']
                },
                'token': token
            }), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@auth_bp.route('/auth/verify', methods=['GET'])
def verify_token():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id_user, nombre, correo, tipo FROM users WHERE id_user = %s", (usuario_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'Usuario no encontrado'}), 404

            return jsonify({
                'valid': True,
                'user_id': user['id_user'],
                'nombre': user['nombre'],
                'correo': user['correo'],
                'tipo': user['tipo']
            }), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()