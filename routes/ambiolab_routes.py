from flask import Blueprint, request, jsonify
from database import get_db_connection_visitas  # Conecta a DB_AMBIOLAB
from werkzeug.security import generate_password_hash, check_password_hash
from auth import generar_token, verificar_token_request
import random
import string
import io
import base64
import qrcode
from datetime import datetime

ambiolab_bp = Blueprint('ambiolab', __name__, url_prefix='/api')

# -------------------- AUTENTICACIÓN --------------------
@ambiolab_bp.route('/auth/register', methods=['POST'])
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
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/users/<int:id>', methods=['PUT'])
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
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/users', methods=['GET'])
def obtener_usuarios():
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    correo = data.get('correo')
    password = data.get('password')

    if not correo or not password:
        return jsonify({'error': 'Correo y contraseña son requeridos'}), 400

    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/auth/verify', methods=['GET'])
def verify_token():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    db = None
    try:
        db = get_db_connection_visitas()
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

# -------------------- VISITAS --------------------
@ambiolab_bp.route('/visitas/codigo/<string:codigo>', methods=['GET'])
def obtener_visita_por_codigo_ambiolab(codigo):
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/visitas', methods=['GET'])
def obtener_visitas_filtradas_ambiolab():
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

@ambiolab_bp.route('/visitas', methods=['POST'])
def crear_visita_ambiolab():
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

@ambiolab_bp.route('/visitas/<int:id>', methods=['PUT'])
def actualizar_visita_ambiolab(id):
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
        escaneado = data.get('escaneado')
        fecha_escaneo = data.get('fecha_escaneo')

        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            query = """
                UPDATE visitas
                SET nombre=%s, apellidoPaterno=%s, apellidoMaterno=%s, lugar=%s,
                    fecha=%s, departamento=%s, detalle=%s, codigo=%s, escaneado=%s, fecha_escaneo=%s
                WHERE id=%s
            """
            cursor.execute(query, (nombre, apellidoPaterno, apellidoMaterno, lugar, fecha, departamento, detalle, codigo, escaneado, fecha_escaneo, id))
            db.commit()

            if cursor.rowcount == 0:
                return jsonify({'error': 'Visita no encontrada'}), 404

        return jsonify({'message': 'Visita actualizada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@ambiolab_bp.route('/visitas/<int:id>', methods=['DELETE'])
def eliminar_visita_ambiolab(id):
    db = None
    try:
        db = get_db_connection_visitas()
        cursor = db.cursor()
        
        cursor.execute("SELECT id FROM visitas WHERE id = %s", (id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Visita no encontrada'}), 404
        
        db.begin()
        cursor.execute("DELETE FROM notificaciones WHERE visita_id = %s", (id,))
        cursor.execute("DELETE FROM visitas WHERE id = %s", (id,))
        db.commit()
        
        return jsonify({'message': 'Visita eliminada correctamente'}), 200
    except Exception as e:
        if db:
            db.rollback()
        return jsonify({'error': f'Error al eliminar la visita: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@ambiolab_bp.route('/visitas/<int:id>', methods=['GET'])
def obtener_visita_por_id_ambiolab(id):
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

@ambiolab_bp.route('/visitas/<int:id>/escaneado', methods=['PATCH'])
def marcar_visita_escaneada(id):
    db = None
    try:
        data = request.json
        escaneado = data.get('escaneado', True)
        fecha_escaneo = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db = get_db_connection_visitas()
        with db.cursor() as cursor:
            cursor.execute("SELECT escaneado FROM visitas WHERE id = %s", (id,))
            visita_actual = cursor.fetchone()
            
            if not visita_actual:
                return jsonify({'error': 'Visita no encontrada'}), 404
            
            query = """
                UPDATE visitas 
                SET escaneado = %s, fecha_escaneo = %s 
                WHERE id = %s
            """
            cursor.execute(query, (escaneado, fecha_escaneo, id))
            
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

# -------------------- PEDIDOS --------------------
@ambiolab_bp.route('/pedidos', methods=['GET'])
def obtener_pedidos():
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/pedidos/<int:id_pedidos>', methods=['GET'])
def obtener_pedido_por_id(id_pedidos):
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/pedidos', methods=['POST'])
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

        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/pedidos/<int:id_pedidos>', methods=['PUT'])
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

        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/pedidos/<int:id_pedidos>', methods=['DELETE'])
def eliminar_pedido(id_pedidos):
    db = None
    try:
        db = get_db_connection_visitas()
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
@ambiolab_bp.route('/news', methods=['POST'])
def crear_noticia():
    db = None
    try:
        data = request.json
        titulo_new = data.get('titulo_new')
        detalle_new = data.get('detalle_new')

        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/news', methods=['GET'])
def obtener_todas_las_noticias():
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/news/<int:id>', methods=['PUT'])
def actualizar_noticia(id):
    db = None
    try:
        data = request.json
        titulo_new = data.get('titulo_new')
        detalle_new = data.get('detalle_new')

        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/news/<int:id>', methods=['DELETE'])
def eliminar_noticia(id):
    db = None
    try:
        db = get_db_connection_visitas()
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

# -------------------- NOTIFICACIONES --------------------
@ambiolab_bp.route('/notificaciones', methods=['GET'])
def obtener_notificaciones():
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/notificaciones/unread-count', methods=['GET'])
def obtener_contador_no_leidas():
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/notificaciones/read-all', methods=['PUT'])
def marcar_todas_leidas():
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/notificaciones/<int:id>/read', methods=['PUT'])
def marcar_notificacion_leida(id):
    db = None
    try:
        db = get_db_connection_visitas()
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

@ambiolab_bp.route('/notificaciones/<int:id>', methods=['DELETE'])
def eliminar_notificacion(id):
    db = None
    cursor = None
    try:
        db = get_db_connection_visitas()
        cursor = db.cursor()
        
        cursor.execute("SELECT id, visita_id FROM notificaciones WHERE id = %s", (id,))
        notificacion = cursor.fetchone()
        
        if not notificacion:
            return jsonify({'error': 'Notificación no encontrada'}), 404
        
        db.begin()
        
        try:
            cursor.execute("UPDATE notificaciones SET visita_id = NULL WHERE id = %s", (id,))
            cursor.execute("DELETE FROM notificaciones WHERE id = %s", (id,))
            db.commit()
            
            return jsonify({"message": "Notificación eliminada correctamente"}), 200
        except Exception as e:
            db.rollback()
            raise e
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

@ambiolab_bp.route('/notificaciones/visita/<int:visita_id>', methods=['DELETE'])
def eliminar_notificaciones_por_visita(visita_id):
    db = None
    cursor = None
    try:
        db = get_db_connection_visitas()
        cursor = db.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM notificaciones WHERE visita_id = %s", (visita_id,))
        count = cursor.fetchone()['count']
        
        if count == 0:
            return jsonify({"message": "No hay notificaciones asociadas a esta visita"}), 200
        
        db.begin()
        
        try:
            cursor.execute("UPDATE notificaciones SET visita_id = NULL WHERE visita_id = %s", (visita_id,))
            cursor.execute("DELETE FROM notificaciones WHERE visita_id IS NULL")
            deleted_count = cursor.rowcount
            db.commit()
            
            return jsonify({"message": f"{deleted_count} notificaciones eliminadas correctamente"}), 200
        except Exception as e:
            db.rollback()
            raise e
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()