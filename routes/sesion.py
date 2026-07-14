from flask import Blueprint, request, jsonify
from database import get_db_connection_usuarios
from auth import verificar_token_request
from datetime import timedelta
from routes.push_routes import enviar_push
from routes.sse import notificar_usuario, notificar_usuarios

def serializar(row):
    result = {}
    for k, v in row.items():
        if isinstance(v, timedelta):
            total = int(v.total_seconds())
            result[k] = f"{total // 3600:02}:{(total % 3600) // 60:02}"
        elif hasattr(v, 'isoformat'):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result

sesion_bp = Blueprint('sesion', __name__, url_prefix='/api/sesiones')


@sesion_bp.route('', methods=['POST'])
def crear_sesion():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    data = request.json
    titulo      = data.get('titulo')
    sala        = data.get('sala')
    code        = data.get('code')
    capacidad   = data.get('capacidad')
    detalles    = data.get('detalles')
    fecha       = data.get('fecha')
    hora_inicio = data.get('hora_inicio')
    hora_fin    = data.get('hora_fin')
    zona        = data.get('zona')
    tipo        = data.get('tipo', 'publico')
    password    = data.get('password') if tipo == 'privado' else None

    if not titulo:
        return jsonify({'error': 'titulo es requerido'}), 400

    if tipo not in ('publico', 'privado'):
        return jsonify({'error': 'tipo debe ser publico o privado'}), 400

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            if code:
                cursor.execute("SELECT id FROM sesion WHERE code = %s", (code,))
                if cursor.fetchone():
                    return jsonify({'error': 'El code ya está en uso'}), 400

            cursor.execute(
                """INSERT INTO sesion
                   (titulo, sala, code, capacidad, detalles, fecha, hora_inicio, hora_fin, zona, tipo, password, id_user_organizador)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (titulo, sala, code, capacidad, detalles, fecha, hora_inicio, hora_fin, zona, tipo, password, usuario_id)
            )
            db.commit()
            return jsonify({'message': 'Sesión creada', 'id': cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@sesion_bp.route('', methods=['GET'])
def obtener_sesiones():
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.titulo, s.sala, s.code, s.capacidad, s.detalles,
                       s.fecha, s.hora_inicio, s.hora_fin, s.zona, s.tipo, s.created_at,
                       u.username AS organizador
                FROM sesion s
                LEFT JOIN users u ON s.id_user_organizador = u.id
                ORDER BY s.fecha DESC, s.hora_inicio ASC
            """)
            sesiones = [serializar(s) for s in cursor.fetchall()]
            return jsonify(sesiones), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@sesion_bp.route('/<int:id>', methods=['GET'])
def obtener_sesion(id):
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.titulo, s.sala, s.code, s.capacidad, s.detalles,
                       s.fecha, s.hora_inicio, s.hora_fin, s.zona, s.tipo, s.created_at,
                       u.username AS organizador
                FROM sesion s
                LEFT JOIN users u ON s.id_user_organizador = u.id
                WHERE s.id = %s
            """, (id,))
            sesion = cursor.fetchone()
            if not sesion:
                return jsonify({'error': 'Sesión no encontrada'}), 404
            return jsonify(serializar(sesion)), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@sesion_bp.route('/<int:id>', methods=['PUT'])
def editar_sesion(id):
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    data = request.json
    titulo      = data.get('titulo')
    sala        = data.get('sala')
    code        = data.get('code')
    capacidad   = data.get('capacidad')
    detalles    = data.get('detalles')
    fecha       = data.get('fecha')
    hora_inicio = data.get('hora_inicio')
    hora_fin    = data.get('hora_fin')
    zona        = data.get('zona')
    tipo        = data.get('tipo', 'publico')
    password    = data.get('password') if tipo == 'privado' else None

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM sesion WHERE id = %s AND id_user_organizador = %s", (id, usuario_id))
            if not cursor.fetchone():
                return jsonify({'error': 'Sesión no encontrada o sin permiso'}), 404

            if code:
                cursor.execute("SELECT id FROM sesion WHERE code = %s AND id != %s", (code, id))
                if cursor.fetchone():
                    return jsonify({'error': 'El code ya está en uso'}), 400

            cursor.execute("SELECT sala FROM sesion WHERE id = %s", (id,))
            sala_anterior = cursor.fetchone()['sala']

            cursor.execute(
                """UPDATE sesion SET titulo=%s, sala=%s, code=%s, capacidad=%s, detalles=%s,
                   fecha=%s, hora_inicio=%s, hora_fin=%s, zona=%s, tipo=%s, password=%s
                   WHERE id=%s""",
                (titulo, sala, code, capacidad, detalles, fecha, hora_inicio, hora_fin, zona, tipo, password, id)
            )
            db.commit()

            cursor.execute("""
                SELECT DISTINCT u.id FROM asistencia_sesion asis
                JOIN asistentes a ON asis.id_asistente = a.id
                JOIN users u ON u.email = a.email
                WHERE asis.id_sesion = %s
            """, (id,))
            mensaje = f'Sala: {sala or "—"} (antes: {sala_anterior or "—"}), Fecha: {fecha or "—"}' if sala != sala_anterior else f'Fecha: {fecha or "—"}, Sala: {sala or "—"}'
            ids_inscritos = [row['id'] for row in cursor.fetchall()]

            for uid in ids_inscritos:
                enviar_push(uid, '📝 Evento actualizado', f'"{titulo}" fue modificado. {mensaje}')

            # 👇 FIX: incluir SIEMPRE al organizador en la lista de destinatarios del SSE
            destinatarios = set(ids_inscritos)
            destinatarios.add(usuario_id)

            sesion_actualizada = serializar({
                'id': id, 'titulo': titulo, 'sala': sala, 'code': code,
                'capacidad': capacidad, 'detalles': detalles, 'fecha': fecha,
                'hora_inicio': hora_inicio, 'hora_fin': hora_fin, 'zona': zona, 'tipo': tipo
            })
            notificar_usuarios(list(destinatarios), 'sesion_actualizada', sesion_actualizada)

            return jsonify({'message': 'Sesión actualizada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@sesion_bp.route('/<int:id>', methods=['DELETE'])
def eliminar_sesion(id):
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM sesion WHERE id = %s AND id_user_organizador = %s", (id, usuario_id))
            if not cursor.fetchone():
                return jsonify({'error': 'Sesión no encontrada o sin permiso'}), 404

            cursor.execute("SELECT titulo FROM sesion WHERE id = %s", (id,))
            titulo_sesion = cursor.fetchone()['titulo']

            cursor.execute("""
                SELECT DISTINCT u.id FROM asistencia_sesion asis
                JOIN asistentes a ON asis.id_asistente = a.id
                JOIN users u ON u.email = a.email
                WHERE asis.id_sesion = %s
            """, (id,))
            ids_inscritos = [row['id'] for row in cursor.fetchall()]

            cursor.execute("DELETE FROM sesion WHERE id = %s", (id,))
            db.commit()

            for uid in ids_inscritos:
                enviar_push(uid, '🗑️ Evento cancelado', f'El evento "{titulo_sesion}" fue eliminado por el organizador.')

            # 👇 FIX: incluir al organizador también aquí
            destinatarios = set(ids_inscritos)
            destinatarios.add(usuario_id)
            notificar_usuarios(list(destinatarios), 'sesion_eliminada', {'id': id})

            return jsonify({'message': 'Sesión eliminada'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()