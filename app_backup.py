import pymysql
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
import random
import string
import io
import base64
import qrcode
from upload_routes import upload_bp

app = Flask(__name__)
CORS(app)

app.config['UPLOAD_FOLDER'] = '/var/www/request'

app.register_blueprint(upload_bp)

# Clave secreta para JWT
SECRET_KEY = 'AdminTics222310'

# -------------------- JWT --------------------
def generar_token(usuario_id):
    payload = {
        'usuario_id': usuario_id,
        'exp': datetime.utcnow() + timedelta(hours=8)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def verificar_token_request():
    token = request.headers.get('Authorization')
    if not token:
        return None
    try:
        if token.startswith('Bearer '):
            token = token.split(' ')[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['usuario_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# -------------------- CONEXIONES --------------------
def get_db_connection_usuarios():
    return pymysql.connect(
        host="189.136.70.8",
        user="adminfull",
        password="222310342",
        database="ambiolab",
        port=53307,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_db_connection_visitas():
    return pymysql.connect(
        host="189.136.67.84",
        user="AdminTics",
        password="AdminTics0012",
        database="labsa",
        cursorclass=pymysql.cursors.DictCursor
    )

# -------------------- AUTENTICACIÓN --------------------
@app.route('/auth/register', methods=['POST'])
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

@app.route('/auth/login', methods=['POST'])
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
# --------------------- VALIDACION DE TOKEN ---------------
@app.route('/auth/verify', methods=['GET'])
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

# -------------------- VISITAS AMBIOLAB --------------------
@app.route('/visitam', methods=['GET'])
def obtener_visitas_filtradas():
    db = None
    try:
        nombre = request.args.get('nombre')
        departamento = request.args.get('departamento')
        hora = request.args.get('hora')
        dia = request.args.get('dia')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        offset = (page - 1) * limit

        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            base_query = """
                SELECT id, nombre, apellidoPaterno, apellidoMaterno, lugar,
                    DATE_FORMAT(fecha, '%%Y-%%m-%%d') as dia,
                    TIME_FORMAT(fecha, '%%H:%%i:%%s') as hora,
                    departamento, detalle, codigo, escaneado, fecha_escaneo
                FROM visitas WHERE 1=1
            """
            conditions = []
            params = []

            if nombre:
                conditions.append("nombre LIKE %s")
                params.append(f"%{nombre}%")
            if departamento:
                conditions.append("departamento LIKE %s")
                params.append(f"%{departamento}%")
            if hora:
                conditions.append("TIME_FORMAT(fecha, '%%H') = %s")
                params.append(hora)
            if dia:
                conditions.append("DATE(fecha) = %s")
                params.append(dia)

            if conditions:
                base_query += " AND " + " AND ".join(conditions)

            count_query = "SELECT COUNT(*) as total FROM (" + base_query + ") as temp"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']

            base_query += " ORDER BY fecha DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(base_query, params)
            visitas = cursor.fetchall()

        return jsonify({
            "data": visitas,
            "page": page,
            "limit": limit,
            "total": total
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitam', methods=['POST'])
def crear_visita():
    db = None
    try:
        data = request.json
        nombre = data.get('nombre')
        apellidoPaterno = data.get('apellidoPaterno')
        apellidoMaterno = data.get('apellidoMaterno')
        lugar = data.get('lugar')
        fecha = data.get('fecha')
        departamento = data.get('departamento')
        detalle = data.get('detalle')

        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                INSERT INTO visitas
                (nombre, apellidoPaterno, apellidoMaterno, lugar, fecha, departamento, detalle, codigo, escaneado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, apellidoPaterno, apellidoMaterno, lugar, fecha, departamento, detalle, codigo, False))
            db.commit()
            new_id = cursor.lastrowid

        qr_img = qrcode.make(codigo)
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        return jsonify({
            'message': 'Visita creada',
            'id': new_id,
            'codigo': codigo,
            'qr_base64': qr_base64
        }), 201
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitam/<int:id>', methods=['PUT'])
def actualizar_visita(id):
    db = None
    try:
        data = request.json
        nombre = data.get('nombre')
        apellidoPaterno = data.get('apellidoPaterno')
        apellidoMaterno = data.get('apellidoMaterno')
        lugar = data.get('lugar')
        fecha = data.get('fecha')
        departamento = data.get('departamento')
        detalle = data.get('detalle')
        codigo = data.get('codigo')

        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                UPDATE visitas
                SET nombre=%s, apellidoPaterno=%s, apellidoMaterno=%s, lugar=%s,
                    fecha=%s, departamento=%s, detalle=%s, codigo=%s
                WHERE id=%s
            """
            cursor.execute(query, (nombre, apellidoPaterno, apellidoMaterno, lugar, fecha, departamento, detalle, codigo, id))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Visita no encontrada'}), 404

        return jsonify({'message': 'Visita actualizada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitam/<int:id>', methods=['DELETE'])
def eliminar_visita(id):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = "DELETE FROM visitas WHERE id = %s"
            cursor.execute(query, (id,))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Visita no encontrada'}), 404

        return jsonify({'message': 'Visita eliminada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitam/<int:id>', methods=['GET'])
def obtener_visita_por_id(id):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = "SELECT * FROM visitas WHERE id = %s"
            cursor.execute(query, (id,))
            visita = cursor.fetchone()

            if not visita:
                return jsonify({'error': 'Visita no encontrada'}), 404

            return jsonify(visita), 200
    except Exception as e:
        return jsonify({'error': 'Error al obtener la visita', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitam/codigo/<string:codigo>', methods=['GET'])
def obtener_visita_por_codigo(codigo):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                SELECT id, nombre, apellidoPaterno, apellidoMaterno, lugar,
                    DATE_FORMAT(fecha, '%%Y-%%m-%%d') as dia,
                    TIME_FORMAT(fecha, '%%H:%%i:%%s') as hora,
                    departamento, detalle, codigo, escaneado, fecha_escaneo
                FROM visitas
                WHERE codigo = %s
                LIMIT 1
            """
            cursor.execute(query, (codigo,))
            visita = cursor.fetchone()

        if not visita:
            return jsonify({'error': 'Visita no encontrada'}), 404

        return jsonify(visita), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitam/<int:id>/escaneado', methods=['PATCH'])
def marcar_visita_escaneada(id):
    db = None
    try:
        from datetime import datetime
        
        data = request.json
        escaneado = data.get('escaneado', True)
        fecha_escaneo = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            # Verificar estado actual antes de actualizar
            cursor.execute("SELECT escaneado FROM visitas WHERE id = %s", (id,))
            visita_actual = cursor.fetchone()
            
            if not visita_actual:
                return jsonify({'error': 'Visita no encontrada'}), 404
            
            # Actualizar visita
            query = """
                UPDATE visitas 
                SET escaneado = %s, fecha_escaneo = %s 
                WHERE id = %s
            """
            cursor.execute(query, (escaneado, fecha_escaneo, id))
            
            # Crear notificación solo si cambió de no escaneado a escaneado
            if escaneado and not visita_actual['escaneado']:
                cursor.execute("SELECT nombre, apellidoPaterno FROM visitas WHERE id = %s", (id,))
                visita = cursor.fetchone()
                
                if visita:
                    mensaje = f"{visita['nombre']} {visita['apellidoPaterno']} ha ingresado"
                    cursor.execute(
                        "INSERT INTO notificaciones (visita_id, mensaje, leida) VALUES (%s, %s, %s)",
                        (id, mensaje, False)
                    )
            
            db.commit()
                
        return jsonify({'message': 'Visita marcada como escaneada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

#--------------------- Notificaciones ------------
# Endpoints para notificaciones

@app.route('/notificaciones', methods=['GET'])
def obtener_notificaciones():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                SELECT n.id, n.visita_id, n.mensaje, n.leida, n.created_at,
                       v.nombre, v.apellidoPaterno
                FROM notificaciones n
                LEFT JOIN visitas v ON n.visita_id = v.id
                ORDER BY n.created_at DESC
            """
            cursor.execute(query)
            notificaciones = cursor.fetchall()
        
        return jsonify({"data": notificaciones}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/notificaciones/unread-count', methods=['GET'])
def obtener_contador_no_leidas():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = "SELECT COUNT(*) as count FROM notificaciones WHERE leida = FALSE"
            cursor.execute(query)
            result = cursor.fetchone()
        
        return jsonify({"count": result['count']}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/notificaciones/read-all', methods=['PUT'])
def marcar_todas_leidas():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = "UPDATE notificaciones SET leida = TRUE WHERE leida = FALSE"
            cursor.execute(query)
            db.commit()
        
        return jsonify({"message": "Todas las notificaciones marcadas como leídas"}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/notificaciones/<int:id>/read', methods=['PUT'])
def marcar_notificacion_leida(id):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = "UPDATE notificaciones SET leida = TRUE WHERE id = %s"
            cursor.execute(query, (id,))
            db.commit()
            
            if cursor.rowcount == 0:
                return jsonify({'error': 'Notificación no encontrada'}), 404
        
        return jsonify({"message": "Notificación marcada como leída"}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

# -------------------- VISITAS --------------------
@app.route('/visitas/codigo/<string:codigo>', methods=['GET'])
def obtener_visita_por_codigo_labsa(codigo):
    db = None
    try:
        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            query = """
                SELECT id, nombre, apellidoPaterno, apellidoMaterno, lugar,
                    DATE_FORMAT(fecha, '%%Y-%%m-%%d') as dia,
                    TIME_FORMAT(fecha, '%%H:%%i:%%s') as hora,
                    departamento, detalle, codigo
                FROM visitas
                WHERE codigo = %s
                LIMIT 1
            """
            cursor.execute(query, (codigo,))
            visita = cursor.fetchone()

        if not visita:
            return jsonify({'error': 'Visita no encontrada'}), 404

        return jsonify(visita), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitas', methods=['GET'])
def obtener_visitas_filtradas_labsa():
    db = None
    try:
        nombre = request.args.get('nombre')
        departamento = request.args.get('departamento')
        hora = request.args.get('hora')
        dia = request.args.get('dia')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        offset = (page - 1) * limit

        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            base_query = """
                SELECT id, nombre, apellidoPaterno, apellidoMaterno, lugar,
                    DATE_FORMAT(fecha, '%%Y-%%m-%%d') as dia,
                    TIME_FORMAT(fecha, '%%H:%%i:%%s') as hora,
                    departamento, detalle, codigo
                FROM visitas WHERE 1=1
            """
            conditions = []
            params = []

            if nombre:
                conditions.append("nombre LIKE %s")
                params.append(f"%{nombre}%")
            if departamento:
                conditions.append("departamento LIKE %s")
                params.append(f"%{departamento}%")
            if hora:
                conditions.append("TIME_FORMAT(fecha, '%%H') = %s")
                params.append(hora)
            if dia:
                conditions.append("DATE(fecha) = %s")
                params.append(dia)

            if conditions:
                base_query += " AND " + " AND ".join(conditions)

            count_query = "SELECT COUNT(*) as total FROM (" + base_query + ") as temp"
            cursor.execute(count_query, params)
            total = cursor.fetchone()['total']

            base_query += " ORDER BY fecha DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            cursor.execute(base_query, params)
            visitas = cursor.fetchall()

        return jsonify({
            "data": visitas,
            "page": page,
            "limit": limit,
            "total": total
        }), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitas', methods=['POST'])
def crear_visita_labsa():
    db = None
    try:
        data = request.json
        nombre = data.get('nombre')
        apellidoPaterno = data.get('apellidoPaterno')
        apellidoMaterno = data.get('apellidoMaterno')
        lugar = data.get('lugar')
        fecha = data.get('fecha')
        departamento = data.get('departamento')
        detalle = data.get('detalle')

        codigo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            query = """
                INSERT INTO visitas
                (nombre, apellidoPaterno, apellidoMaterno, lugar, fecha, departamento, detalle, codigo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, apellidoPaterno, apellidoMaterno, lugar, fecha, departamento, detalle, codigo))
            db.commit()
            new_id = cursor.lastrowid

        qr_img = qrcode.make(codigo)
        buffered = io.BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        return jsonify({
            'message': 'Visita creada',
            'id': new_id,
            'codigo': codigo,
            'qr_base64': qr_base64
        }), 201
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitas/<int:id>', methods=['PUT'])
def actualizar_visita_labsa(id):
    db = None
    try:
        data = request.json
        nombre = data.get('nombre')
        apellidoPaterno = data.get('apellidoPaterno')
        apellidoMaterno = data.get('apellidoMaterno')
        lugar = data.get('lugar')
        fecha = data.get('fecha')
        departamento = data.get('departamento')
        detalle = data.get('detalle')
        codigo = data.get('codigo')

        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            query = """
                UPDATE visitas
                SET nombre=%s, apellidoPaterno=%s, apellidoMaterno=%s, lugar=%s,
                    fecha=%s, departamento=%s, detalle=%s, codigo=%s
                WHERE id=%s
            """
            cursor.execute(query, (nombre, apellidoPaterno, apellidoMaterno, lugar, fecha, departamento, detalle, codigo, id))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Visita no encontrada'}), 404

        return jsonify({'message': 'Visita actualizada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitas/<int:id>', methods=['DELETE'])
def eliminar_visita_labsa(id):
    db = None
    try:
        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            query = "DELETE FROM visitas WHERE id = %s"
            cursor.execute(query, (id,))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Visita no encontrada'}), 404

        return jsonify({'message': 'Visita eliminada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/visitas/<int:id>', methods=['GET'])
def obtener_visita_por_id_labsa(id):
    db = None
    try:
        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            query = "SELECT * FROM visitas WHERE id = %s"
            cursor.execute(query, (id,))
            visita = cursor.fetchone()

            if not visita:
                return jsonify({'error': 'Visita no encontrada'}), 404

            return jsonify(visita), 200
    except Exception as e:
        return jsonify({'error': 'Error al obtener la visita', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

# -------------------- PEDIDOS --------------------
@app.route('/pedidos', methods=['GET'])
def obtener_pedidos():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                SELECT p.*, u.nombre AS modificado_por_nombre, u.app AS modificado_por_app
                FROM pedidos p
                LEFT JOIN users u ON p.modificado_por = u.id_user
                ORDER BY p.id_pedidos DESC
            """
            cursor.execute(query)
            pedidos = cursor.fetchall()
            return jsonify(pedidos), 200
    except Exception as e:
        return jsonify({'error': 'Error al obtener pedidos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/pedidos/<int:id_pedidos>', methods=['GET'])
def obtener_pedido_por_id(id_pedidos):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM pedidos WHERE id_pedidos = %s", (id_pedidos,))
            pedido = cursor.fetchone()
            if not pedido:
                return jsonify({'error': 'Pedido no encontrado'}), 404
            return jsonify(pedido), 200
    except Exception as e:
        return jsonify({'error': 'Error al obtener el pedido', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/pedidos', methods=['POST'])
def crear_pedido():
    db = None
    try:
        data = request.json
        nombre = data.get('nombre')
        norma = data.get('norma')
        estatus = data.get('estatus', 'pendiente')
        fecha_inicio = data.get('fecha_inicio')
        fecha_final = data.get('fecha_final')
        comentario = data.get('comentario')
        precio = data.get('precio')

        if not nombre:
            return jsonify({'error': 'El campo nombre es obligatorio'}), 400

        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                INSERT INTO pedidos (nombre, norma, estatus, fecha_inicio, fecha_final, comentario, precio)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nombre, norma, estatus, fecha_inicio, fecha_final, comentario, precio))
            db.commit()
            nuevo_id = cursor.lastrowid

        return jsonify({'message': 'Pedido creado', 'id_pedidos': nuevo_id}), 201
    except Exception as e:
        return jsonify({'error': 'Error al crear el pedido', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/pedidos/<int:id_pedidos>', methods=['PUT'])
def actualizar_pedido(id_pedidos):
    db = None
    try:
        usuario_id = verificar_token_request()
        if not usuario_id:
            return jsonify({'error': 'Token inválido o expirado'}), 401

        data = request.json
        nombre = data.get('nombre')
        norma = data.get('norma')
        estatus = data.get('estatus')
        fecha_inicio = data.get('fecha_inicio')
        fecha_final = data.get('fecha_final')
        comentario = data.get('comentario')
        precio = data.get('precio')

        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                UPDATE pedidos
                SET nombre=%s, norma=%s, estatus=%s, fecha_inicio=%s,
                    fecha_final=%s, comentario=%s, precio=%s, modificado_por=%s
                WHERE id_pedidos=%s
            """
            cursor.execute(query, (nombre, norma, estatus, fecha_inicio, fecha_final, comentario, precio, usuario_id, id_pedidos))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Pedido no encontrado'}), 404

        return jsonify({'message': 'Pedido actualizado'}), 200
    except Exception as e:
        return jsonify({'error': 'Error al actualizar el pedido', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/pedidos/<int:id_pedidos>', methods=['DELETE'])
def eliminar_pedido(id_pedidos):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM pedidos WHERE id_pedidos = %s", (id_pedidos,))
            db.commit()
            if cursor.rowcount == 0:
                return jsonify({'error': 'Pedido no encontrado'}), 404
            return jsonify({'message': 'Pedido eliminado'}), 200
    except Exception as e:
        return jsonify({'error': 'Error al eliminar el pedido', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

# -------------------- NOTICIAS --------------------
@app.route('/news', methods=['POST'])
def crear_noticia():
    db = None
    try:
        data = request.json
        titulo_new = data.get('titulo_new')
        detalle_new = data.get('detalle_new')

        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                INSERT INTO news (titulo_new, detalle_new)
                VALUES (%s, %s)
            """
            cursor.execute(query, (titulo_new, detalle_new))
            db.commit()
            new_id = cursor.lastrowid

        return jsonify({
            'message': 'Noticia creada',
            'id': new_id
        }), 201
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/news', methods=['GET'])
def obtener_todas_las_noticias():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                SELECT id_new, titulo_new, detalle_new
                FROM news
            """
            cursor.execute(query)
            noticias = cursor.fetchall()

        return jsonify(noticias), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/news/<int:id>', methods=['PUT'])
def actualizar_noticia(id):
    db = None
    try:
        data = request.json
        titulo_new = data.get('titulo_new')
        detalle_new = data.get('detalle_new')

        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = """
                UPDATE news
                SET titulo_new=%s, detalle_new=%s
                WHERE id_new=%s
            """
            cursor.execute(query, (titulo_new, detalle_new, id))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Noticia no encontrada'}), 404

        return jsonify({'message': 'Noticia actualizada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@app.route('/news/<int:id>', methods=['DELETE'])
def eliminar_noticia(id):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            query = "DELETE FROM news WHERE id_new = %s"
            cursor.execute(query, (id,))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Noticia no encontrada'}), 404

        return jsonify({'message': 'Noticia eliminada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

# -------------------- MAIN --------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
