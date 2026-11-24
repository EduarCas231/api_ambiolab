from gevent import monkey
monkey.patch_all(thread=False)

from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import os
import jwt
import datetime
import math
from functools import wraps
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit, join_room, leave_room
from decimal import Decimal

load_dotenv()

app = Flask(__name__)
CORS(app)


socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')


user_sid_map = {}

SECRET_KEY = os.getenv('SECRET_KEY', 'clave')


def convert_decimals(obj):
    """Convierte objetos Decimal, datetime y otros tipos no JSON-serializables."""
    if obj is None:
        return None
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, datetime.time):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_decimals(item) for item in obj]
    return obj


def json_response(data, status=200):
    """Retorna JSON convirtiendo Decimals y datetimes a tipos serializables."""
    return jsonify(convert_decimals(data)), status


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'Message': 'Token requerido'}), 401
        try:
            jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'Message': 'Token expirado'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'Message': 'Token inválido'}), 401
        return f(*args, **kwargs)
    return decorated


def conection_db():
    try:
        conexion = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            port=int(os.getenv('DB_PORT')),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        return conexion
    except Exception as e:
        print("ERROR MYSQL:", e)
        return None


def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """Calcula distancia en km entre 2 puntos GPS (fórmula Haversine)."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371 
    lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return round(R * c, 2)


def calcular_tiempo_estimado(distancia_km, velocidad_kmh=40):
    """Tiempo estimado en minutos. Velocidad promedio 40 km/h."""
    if distancia_km is None:
        return None
    return round((distancia_km / velocidad_kmh) * 60, 2)


##ENDPOINTS DE CABALLOS


@app.route('/caballos', methods=['GET'])
@token_required
def get_caballos():
    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor(dictionary=True)
        query = "SELECT * FROM caballo"
        cursor.execute(query)
        caballos = cursor.fetchall()
        cursor.close()
        conexion.close()
        return json_response(caballos, 200)
    return jsonify({'message' : 'Error al conectar a la base de datos'}), 500 

@app.route('/caballo', methods=['POST'])
@token_required
def create_caballo():
    data = request.get_json()
    nombre = data.get('nombre')
    fecha_nacimiento = data.get('fecha de nacimiento')
    raza = data.get('raza')
    sexo = data.get('sexo')
    altura = data.get('altura')
    peso = data.get('peso')
    color = data.get('color')
    tipo_sangre = data.get('tipo de sangre')
    id_usuario = data.get('id_usuario')

    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor()
        query = "INSERT INTO caballo (nombre, fecha_nacimiento, raza, sexo, altura, peso, color, tipo_sangre, id_usuario) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (nombre, fecha_nacimiento, raza, sexo, altura, peso, color, tipo_sangre, id_usuario)
        cursor.execute(query, values)
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({'Message': 'Caballos creado correctamente'}), 201
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500


@app.route('/caballo/<int:id>', methods=['PUT'])
@token_required
def update_caballo(id): 

    data = request.get_json()
    nombre = data.get('nombre')
    fecha_nacimiento = data.get('fecha de nacimiento')
    raza = data.get('raza')
    sexo = data.get('sexo')
    altura = data.get('altura')
    peso = data.get('peso')
    color = data.get('color')
    tipo_sangre = data.get('tipo de sangre')

    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor()
        query = "UPDATE caballo SET nombre=%s, fecha_nacimiento=%s, raza=%s, sexo=%s, altura=%s, peso=%s, color=%s, tipo_sangre=%s WHERE id=%s"
        values = (nombre, fecha_nacimiento, raza, sexo, altura, peso, color, tipo_sangre, id)
        cursor.execute(query, values)
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({'Message': 'Caballo actualizado correctamente'}), 200
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500



@app.route('/caballos/usuario/<int:id_usuario>', methods=['GET'])
@token_required
def get_caballos_by_usuario(id_usuario):
    conexion = conection_db()
    if conexion:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM caballo WHERE id_usuario = %s", (id_usuario,))
        caballos = cursor.fetchall()
        cursor.close()
        conexion.close()
        return json_response(caballos, 200)
    return jsonify({'Message': 'Error al conectar'}), 500


@app.route('/caballos/<int:id>', methods=['DELETE'])
@token_required

def delete_caballo(id):
    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor()
        query = "DELETE FROM caballo WHERE id=%s"
        cursor.execute(query, (id,))
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({'Message': 'Caballo eliminado correctamente'}), 200
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500

##ENDPOINTS DE USUARIOS

@app.route('/user_c', methods=['POST'])
def crear_user():
    data = request.get_json()
    nombre = data.get('nombre')
    numero_telefono = data.get('numero_telefono')
    email = data.get('email')
    password = data.get('password')
    tipo_usuario = data.get('tipo_usuario', 'usuario')
    gps_latitud = data.get('gps_latitud')
    gps_longitud = data.get('gps_longitud')

    conexion = conection_db()


    if conexion:
        cursor = conexion.cursor()
        query = "INSERT INTO usuario (nombre, numero_telefono, email, password, tipo_usuario, gps_latitud, gps_longitud) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (nombre, numero_telefono, email, password, tipo_usuario, gps_latitud, gps_longitud)
        cursor.execute(query, values)
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({'Message': 'Usuario creado correctamente'}), 201
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500



@app.route('/user/<int:id>', methods=['PUT'])
def update_user(id):
    data = request.get_json()
    nombre = data.get('nombre')
    numero_telefono = data.get('numero_telefono')
    email = data.get('email')
    password = data.get('password')
    tipo_usuario = data.get('tipo_usuario')
    gps_latitud = data.get('gps_latitud')
    gps_longitud = data.get('gps_longitud')

    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor()
        query = "UPDATE usuario SET nombre=%s, numero_telefono=%s, email=%s, password=%s, tipo_usuario=%s, gps_latitud=%s, gps_longitud=%s WHERE id=%s"
        values = (nombre, numero_telefono, email, password, tipo_usuario, gps_latitud, gps_longitud, id)
        cursor.execute(query, values)
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({'Message': 'Usuario actualizado correctamente'}), 200
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500


@app.route('/users', methods=['GET'])
def get_user():
    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor(dictionary=True)
        query = "SELECT * FROM usuario" 
        cursor.execute(query)
        users = cursor.fetchall()
        cursor.close()
        conexion.close()
        return json_response(users, 200)
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500


@app.route('/', methods=['GET'])
def health():
    return jsonify({'Message': 'API correctamente funcionando'}), 200



@app.route('/auth', methods=['POST'])
def authenticate():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    tipo_usuario = data.get('tipo_usuario')

    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor(dictionary=True)
        query = "SELECT * FROM usuario WHERE email=%s AND password=%s"
        cursor.execute(query, (email, password))
        user = cursor.fetchone()
        cursor.close()
        conexion.close()
        if user:
            token = jwt.encode({
                'id': user['id'],
                'email': user['email'],
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
            }, SECRET_KEY, algorithm='HS256')
            return json_response({'Message': 'Autenticación exitosa', 'User': user, 'token': token}, 200)
        return jsonify({'Message': 'Credenciales inválidas'}), 401
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500


##carro endpoints
@app.route('/carros', methods= ['GET'])
@token_required

def get_carro():
    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor(dictionary=True)
        query = "SELECT * FROM carro"
        cursor.execute(query)
        carro = cursor.fetchall()
        cursor.close()
        conexion.close()
        return json_response(carro, 200)
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500


@app.route('/carro', methods= ['POST'])
@token_required

def crear_carro():
    data = request.get_json()
    modelo = data.get('modelo')
    marca = data.get('marca')
    placa = data.get('placa')
    dimensiones = data.get('dimensiones')
    gps_latitud = data.get('gps_latitud')
    gps_longitud = data.get('gps_longitud')
    id_empleado = data.get('id_empleado')  # ← NUEVO: opcional

    conexion = conection_db()

    if conexion:
        cursor = conexion.cursor()
        query = "INSERT INTO carro (modelo, marca, placa, dimensiones, gps_latitud, gps_longitud, id_empleado) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        values = (modelo, marca, placa, dimensiones, gps_latitud, gps_longitud, id_empleado)
        cursor.execute(query, values)
        conexion.commit()
        cursor.close()
        conexion.close()
        return jsonify({'Message': 'Carro creado correctamente'}), 201
    return jsonify({'Message': 'Error al conectar a la base de datos'}), 500



# ENDPOINTS  flujo de auxilio


@app.route('/mis-caballos/<int:id_usuario>', methods=['GET'])
@token_required
def mis_caballos(id_usuario):
    """
    Devuelve los caballos del usuario para el botón de auxilio.
    Indica si hay que mostrar selector (más de 1 caballo).
    """
    conexion = conection_db()
    if not conexion:
        return jsonify({'Message': 'Error al conectar a la base de datos'}), 500
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM caballo WHERE id_usuario = %s", (id_usuario,))
        caballos = cursor.fetchall()
        return json_response({
            'cantidad': len(caballos),
            'requiere_seleccion': len(caballos) > 1,
            'caballos': caballos
        }, 200)
    finally:
        cursor.close()
        conexion.close()


@app.route('/empleados-disponibles', methods=['GET'])
@token_required
def empleados_disponibles():
    """
    Devuelve empleados ('personal') con su carro y ubicación actual.
    Marca quién está ocupado (con solicitud activa) para que el admin no
    le asigne otra.
    """
    conexion = conection_db()
    if not conexion:
        return jsonify({'Message': 'Error al conectar'}), 500
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                u.id AS id_empleado,
                u.nombre AS empleado_nombre,
                u.numero_telefono,
                u.gps_latitud,
                u.gps_longitud,
                c.id AS id_carro,
                c.modelo, c.marca, c.placa,
                c.gps_latitud AS carro_lat,
                c.gps_longitud AS carro_lng,
                (SELECT COUNT(*) FROM solicitud_auxilio s
                 WHERE s.id_empleado = u.id
                   AND s.estado IN ('asignada','en_camino')) AS activas
            FROM usuario u
            LEFT JOIN carro c ON c.id_empleado = u.id
            WHERE u.tipo_usuario = 'personal'
            ORDER BY activas ASC, u.nombre ASC
        """)
        empleados = cursor.fetchall()
        
        for e in empleados:
            e['ocupado'] = e['activas'] > 0
            e['disponible'] = e['activas'] == 0
        return json_response(empleados, 200)
    finally:
        cursor.close()
        conexion.close()


@app.route('/solicitudes-activas', methods=['GET'])
@token_required
def solicitudes_activas():
    """
    Para que el panel del admin cargue el estado actual al abrir.
    """
    conexion = conection_db()
    if not conexion:
        return jsonify({'Message': 'Error al conectar'}), 500
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*,
                   u.nombre AS usuario_nombre, u.numero_telefono AS usuario_telefono,
                   c.nombre AS caballo_nombre, c.raza, c.sexo, c.color,
                   e.nombre AS empleado_nombre,
                   ca.modelo AS carro_modelo, ca.marca AS carro_marca, ca.placa AS carro_placa
            FROM solicitud_auxilio s
            JOIN usuario u ON u.id = s.id_usuario
            JOIN caballo c ON c.id = s.id_caballo
            LEFT JOIN usuario e ON e.id = s.id_empleado
            LEFT JOIN carro ca ON ca.id = s.id_carro
            WHERE s.estado IN ('pendiente','asignada','en_camino')
            ORDER BY s.fecha_creacion DESC
        """)
        return json_response(cursor.fetchall(), 200)
    finally:
        cursor.close()
        conexion.close()


@app.route('/mis-ordenes/<int:id_empleado>', methods=['GET'])
@token_required
def mis_ordenes(id_empleado):
    """
    Para que el empleado vea sus órdenes activas si cierra/abre la app.
    """
    conexion = conection_db()
    if not conexion:
        return jsonify({'Message': 'Error al conectar'}), 500
    try:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.id AS id_solicitud, s.id_usuario, s.user_lat, s.user_lng,
                   s.estado, s.fecha_asignacion,
                   u.nombre AS usuario_nombre, u.numero_telefono AS usuario_telefono,
                   c.nombre AS caballo_nombre, c.raza, c.sexo, c.color
            FROM solicitud_auxilio s
            JOIN usuario u ON u.id = s.id_usuario
            JOIN caballo c ON c.id = s.id_caballo
            WHERE s.id_empleado = %s
              AND s.estado IN ('asignada','en_camino')
            ORDER BY s.fecha_asignacion DESC
        """, (id_empleado,))
        return json_response(cursor.fetchall(), 200)
    finally:
        cursor.close()
        conexion.close()



# EVENTOS WEBSOCKET


@socketio.on('connect')
def handle_connect():
    """Cliente se conecta. Aún no sabemos quién es hasta que se autentique."""
    print(f"[WS] Cliente conectado: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    """Cliente se desconecta. Limpiar su sid del mapa."""
    usuario_a_eliminar = None
    for uid, sid in user_sid_map.items():
        if sid == request.sid:
            usuario_a_eliminar = uid
            break
    if usuario_a_eliminar:
        del user_sid_map[usuario_a_eliminar]
        print(f"[WS] Usuario {usuario_a_eliminar} desconectado")


@socketio.on('autenticar')
def handle_autenticar(data):
    """
    El cliente manda id_usuario y tipo_usuario tras conectar.
    data = {id_usuario, tipo_usuario}  # 'usuario', 'personal' o 'admin'
    """
    id_usuario = data.get('id_usuario')
    tipo_usuario = data.get('tipo_usuario', 'usuario')

    if not id_usuario:
        return {'status': 'error', 'message': 'Falta id_usuario'}

   
    user_sid_map[id_usuario] = request.sid

    
    join_room(f"user_{id_usuario}")

    
    if tipo_usuario == 'personal':
        join_room('empleados')
    elif tipo_usuario == 'admin':
        join_room('admins')

    print(f"[WS] {tipo_usuario.upper()} {id_usuario} autenticado (sid={request.sid})")
    return {'status': 'ok', 'sid': request.sid}


@socketio.on('nueva_solicitud')
def handle_nueva_solicitud(data):
    """
    Usuario presiona el botón de auxilio.
    data = {id_usuario, id_caballo, user_lat, user_lng}
    → notifica a TODOS los admins en vivo.
    """
    id_usuario = data.get('id_usuario')
    id_caballo = data.get('id_caballo')
    user_lat = data.get('user_lat')
    user_lng = data.get('user_lng')

    conexion = conection_db()
    if not conexion:
        emit('error_solicitud', {'message': 'Error de BD'})
        return

    try:
        cursor = conexion.cursor(dictionary=True)

        
        cursor.execute("SELECT * FROM caballo WHERE id=%s AND id_usuario=%s",
                       (id_caballo, id_usuario))
        if not cursor.fetchone():
            emit('error_solicitud', {'message': 'Caballo no válido'})
            return

        
        cursor.execute("""
            INSERT INTO solicitud_auxilio (id_usuario, id_caballo, user_lat, user_lng, estado)
            VALUES (%s, %s, %s, %s, 'pendiente')
        """, (id_usuario, id_caballo, user_lat, user_lng))
        conexion.commit()
        id_solicitud = cursor.lastrowid

        
        cursor.execute("""
            SELECT s.*,
                   u.nombre AS usuario_nombre, u.numero_telefono AS usuario_telefono,
                   c.nombre AS caballo_nombre, c.raza, c.sexo, c.color, c.altura, c.peso
            FROM solicitud_auxilio s
            JOIN usuario u ON u.id = s.id_usuario
            JOIN caballo c ON c.id = s.id_caballo
            WHERE s.id = %s
        """, (id_solicitud,))
        solicitud = cursor.fetchone()

        
        # Traer empleados disponibles para que el admin pueda asignar
        cursor.execute("""
            SELECT 
                u.id AS id_empleado,
                u.nombre AS empleado_nombre,
                u.numero_telefono,
                u.gps_latitud,
                u.gps_longitud,
                c.id AS id_carro,
                c.modelo, c.marca, c.placa,
                c.gps_latitud AS carro_lat,
                c.gps_longitud AS carro_lng
            FROM usuario u
            LEFT JOIN carro c ON c.id_empleado = u.id
            WHERE u.tipo_usuario = 'personal'
            AND (SELECT COUNT(*) FROM solicitud_auxilio s
                 WHERE s.id_empleado = u.id
                   AND s.estado IN ('asignada','en_camino')) = 0
            ORDER BY u.nombre ASC
        """)
        empleados_disponibles = cursor.fetchall()

        # Emitir alerta con la solicitud Y los empleados disponibles
        socketio.emit('nueva_alerta', convert_decimals({
            'solicitud': solicitud,
            'empleados_disponibles': empleados_disponibles
        }), room='admins')

        
        emit('solicitud_creada', {
            'status': 'ok',
            'id_solicitud': id_solicitud,
            'mensaje': 'Solicitud enviada. Un administrador la atenderá pronto.'
        })

        print(f"[WS] 🚨 Nueva solicitud {id_solicitud} notificada a admins")

    finally:
        cursor.close()
        conexion.close()


@socketio.on('asignar_solicitud')
def handle_asignar_solicitud(data):
    """
    El admin elige empleado y carro para una solicitud.
    data = {id_solicitud, id_admin, id_empleado, id_carro}
    → notifica al USUARIO y al EMPLEADO.
    """
    id_solicitud = data.get('id_solicitud')
    id_admin = data.get('id_admin')
    id_empleado = data.get('id_empleado')
    id_carro = data.get('id_carro')

    conexion = conection_db()
    if not conexion:
        emit('error_asignar', {'message': 'Error de BD'})
        return

    try:
        cursor = conexion.cursor(dictionary=True)

        
        cursor.execute("SELECT * FROM solicitud_auxilio WHERE id=%s AND estado='pendiente'",
                       (id_solicitud,))
        sol = cursor.fetchone()
        if not sol:
            emit('error_asignar', {'message': 'La solicitud ya fue asignada o cancelada'})
            return

        
        cursor.execute("""
            SELECT COUNT(*) AS activas FROM solicitud_auxilio
            WHERE id_empleado=%s AND estado IN ('asignada','en_camino')
        """, (id_empleado,))
        if cursor.fetchone()['activas'] > 0:
            emit('error_asignar', {'message': 'El empleado ya tiene una orden activa'})
            return

       
        cursor.execute("""
            UPDATE solicitud_auxilio
            SET id_admin=%s, id_empleado=%s, id_carro=%s,
                estado='asignada', fecha_asignacion=NOW()
            WHERE id=%s
        """, (id_admin, id_empleado, id_carro, id_solicitud))
        conexion.commit()

        # Traer datos completos para notificar
        cursor.execute("""
            SELECT s.*,
                   u.nombre AS usuario_nombre, u.numero_telefono AS usuario_telefono,
                   c.nombre AS caballo_nombre, c.raza, c.sexo, c.color,
                   e.nombre AS empleado_nombre, e.numero_telefono AS empleado_telefono,
                   ca.modelo AS carro_modelo, ca.marca AS carro_marca,
                   ca.placa AS carro_placa,
                   ca.gps_latitud AS carro_lat, ca.gps_longitud AS carro_lng
            FROM solicitud_auxilio s
            JOIN usuario u ON u.id = s.id_usuario
            JOIN caballo c ON c.id = s.id_caballo
            JOIN usuario e ON e.id = s.id_empleado
            LEFT JOIN carro ca ON ca.id = s.id_carro
            WHERE s.id = %s
        """, (id_solicitud,))
        solicitud_completa = cursor.fetchone()

        # 🔔 1) Notificar al USUARIO
        socketio.emit('empleado_asignado', convert_decimals({
            'id_solicitud': id_solicitud,
            'empleado_nombre': solicitud_completa['empleado_nombre'],
            'empleado_telefono': solicitud_completa['empleado_telefono'],
            'carro': {
                'modelo': solicitud_completa['carro_modelo'],
                'marca': solicitud_completa['carro_marca'],
                'placa': solicitud_completa['carro_placa'],
                'lat': float(solicitud_completa['carro_lat']) if solicitud_completa['carro_lat'] else None,
                'lng': float(solicitud_completa['carro_lng']) if solicitud_completa['carro_lng'] else None
            }
        }), room=f"user_{sol['id_usuario']}")

        # 🔔 2) Notificar al EMPLEADO
        socketio.emit('orden_asignada', convert_decimals({
            'id_solicitud': id_solicitud,
            'id_usuario': sol['id_usuario'],
            'usuario_nombre': solicitud_completa['usuario_nombre'],
            'usuario_telefono': solicitud_completa['usuario_telefono'],
            'user_lat': float(solicitud_completa['user_lat']),
            'user_lng': float(solicitud_completa['user_lng']),
            'caballo': {
                'nombre': solicitud_completa['caballo_nombre'],
                'raza': solicitud_completa['raza'],
                'sexo': solicitud_completa['sexo'],
                'color': solicitud_completa['color']
            }
        }), room=f"user_{id_empleado}")

        # 🔔 3) Confirmar al admin
        emit('asignacion_ok', {
            'status': 'ok',
            'id_solicitud': id_solicitud,
            'mensaje': 'Empleado asignado correctamente'
        })

        print(f"[WS] ✅ Solicitud {id_solicitud} asignada a personal {id_empleado}")

    finally:
        cursor.close()
        conexion.close()


@socketio.on('actualizar_gps')
def handle_actualizar_gps(data):
    """
    El empleado manda su ubicación mientras va en camino.
    data = {id_solicitud, id_usuario, id_empleado, lat, lng}
    → notifica al USUARIO en vivo.
    """
    id_solicitud = data.get('id_solicitud')
    id_usuario = data.get('id_usuario')
    id_empleado = data.get('id_empleado')
    lat = data.get('lat')
    lng = data.get('lng')

    # Notificar SOLO al usuario dueño de la solicitud → ve el carro moverse
    socketio.emit('empleado_se_mueve', {
        'id_solicitud': id_solicitud,
        'emp_lat': lat,
        'emp_lng': lng
    }, room=f"user_{id_usuario}")

    # Guardar en BD
    conexion = conection_db()
    if conexion:
        try:
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE solicitud_auxilio
                SET emp_lat=%s, emp_lng=%s,
                    estado='en_camino',
                    fecha_en_camino = COALESCE(fecha_en_camino, NOW())
                WHERE id=%s AND estado IN ('asignada','en_camino')
            """, (lat, lng, id_solicitud))
            cursor.execute("""
                UPDATE carro SET gps_latitud=%s, gps_longitud=%s WHERE id_empleado=%s
            """, (lat, lng, id_empleado))
            conexion.commit()
        finally:
            cursor.close()
            conexion.close()


@socketio.on('completar_solicitud')
def handle_completar(data):
    """
    El empleado marca la solicitud como completada.
    data = {id_solicitud, id_usuario}
    """
    id_solicitud = data.get('id_solicitud')
    id_usuario = data.get('id_usuario')

    conexion = conection_db()
    if conexion:
        try:
            cursor = conexion.cursor()
            cursor.execute("""
                UPDATE solicitud_auxilio
                SET estado='completada', fecha_completada=NOW()
                WHERE id=%s
            """, (id_solicitud,))
            conexion.commit()
        finally:
            cursor.close()
            conexion.close()

    # Notificar al usuario
    socketio.emit('solicitud_completada', {'id_solicitud': id_solicitud},
                  room=f"user_{id_usuario}")
    # Notificar a los admins
    socketio.emit('solicitud_finalizada', {'id_solicitud': id_solicitud},
                  room='admins')

    print(f"[WS] ✅ Solicitud {id_solicitud} completada")


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000)