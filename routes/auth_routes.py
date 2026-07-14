from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection_usuarios
from auth import generar_token, verificar_token_request

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'staff')

    if not all([username, email, password]):
        return jsonify({'error': 'username, email y password son requeridos'}), 400

    if role not in ['admin', 'staff', 'speaker']:
        return jsonify({'error': 'role debe ser: admin, staff o speaker'}), 400

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email ya registrado'}), 400

            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
                (username, email, generate_password_hash(password), role)
            )
            db.commit()
            return jsonify({'message': 'Usuario registrado exitosamente'}), 201
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email y password son requeridos'}), 400

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if not user or not check_password_hash(user['password'], password):
                return jsonify({'error': 'Credenciales incorrectas'}), 401

            token = generar_token(user['id'])

            return jsonify({
                'message': 'Login exitoso',
                'token': token,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'role': user['role']
                }
            }), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@auth_bp.route('/users', methods=['GET'])
def get_users():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id, username, email, role, created_at FROM users")
            users = cursor.fetchall()
            return jsonify(users), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@auth_bp.route('/verify', methods=['GET'])
def verify():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id, username, email, role FROM users WHERE id = %s", (usuario_id,))
            user = cursor.fetchone()

            if not user:
                return jsonify({'error': 'Usuario no encontrado'}), 404

            return jsonify({'valid': True, 'user': user}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()
