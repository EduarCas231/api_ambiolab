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

asistente_bp = Blueprint('asistente', __name__, url_prefix='/api/asistentes')


@asistente_bp.route('/unirse', methods=['POST'])
def unirse_sesion():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    data = request.json
    code     = data.get('code')
    password = data.get('password')

    if not code:
        return jsonify({'error': 'El código del evento es requerido'}), 400

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT username, email FROM users WHERE id = %s", (usuario_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'Usuario no encontrado'}), 404

            nombre = user['username']
            email  = user['email']

            cursor.execute("SELECT id, capacidad, tipo, password FROM sesion WHERE code = %s", (code,))
            sesion = cursor.fetchone()
            if not sesion:
                return jsonify({'error': 'Código de evento no válido'}), 404

            if sesion['tipo'] == 'privado':
                if not password or password != sesion['password']:
                    return jsonify({'error': 'Contraseña incorrecta'}), 403

            if sesion['capacidad']:
                cursor.execute("SELECT COUNT(*) AS total FROM asistencia_sesion WHERE id_sesion = %s", (sesion['id'],))
                if cursor.fetchone()['total'] >= sesion['capacidad']:
                    return jsonify({'error': 'El evento ha alcanzado su capacidad máxima'}), 400

            cursor.execute("SELECT id FROM asistentes WHERE email = %s", (email,))
            asistente = cursor.fetchone()
            if asistente:
                id_asistente = asistente['id']
            else:
                cursor.execute(
                    "INSERT INTO asistentes (nombre, email, status) VALUES (%s, %s, 'activo')",
                    (nombre, email)
                )
                id_asistente = cursor.lastrowid

            cursor.execute(
                "SELECT id FROM asistencia_sesion WHERE id_sesion = %s AND id_asistente = %s",
                (sesion['id'], id_asistente)
            )
            if cursor.fetchone():
                return jsonify({'error': 'Ya estás registrado en este evento'}), 400

            cursor.execute(
                "INSERT INTO asistencia_sesion (id_asistente, id_sesion) VALUES (%s, %s)",
                (id_asistente, sesion['id'])
            )
            db.commit()

            # Notificar al organizador que alguien se unió
            cursor.execute("SELECT titulo, id_user_organizador, capacidad FROM sesion WHERE id = %s", (sesion['id'],))
            info = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) AS total FROM asistencia_sesion WHERE id_sesion = %s", (sesion['id'],))
            ocupados = cursor.fetchone()['total']
            enviar_push(info['id_user_organizador'], '👥 Nuevo asistente', f'{nombre} se unió a "{info["titulo"]}" ({ocupados}/{info["capacidad"] or "∞"})')

            cursor.execute("""
                SELECT DISTINCT u.id FROM asistencia_sesion asis
                JOIN asistentes a ON asis.id_asistente = a.id
                JOIN users u ON u.email = a.email
                WHERE asis.id_sesion = %s
            """, (sesion['id'],))
            ids_inscritos = [row['id'] for row in cursor.fetchall()]

            destinatarios = set(ids_inscritos)
            destinatarios.add(info['id_user_organizador'])

            notificar_usuarios(list(destinatarios), 'asistentes_actualizado', {
                'id_sesion': sesion['id'],
                'ocupados': ocupados,
                'capacidad': info['capacidad']
            })
            if info['capacidad'] and ocupados >= info['capacidad']:
                for uid in ids_inscritos:
                    enviar_push(uid, '🔴 Cupo lleno', f'El evento "{info["titulo"]}" ha alcanzado su capacidad máxima.')

            return jsonify({'message': '¡Te has unido al evento exitosamente!'}), 201
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()

@asistente_bp.route('/sesion/<int:id_sesion>', methods=['GET'])
def obtener_asistentes(id_sesion):
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT id, capacidad FROM sesion WHERE id = %s", (id_sesion,))
            sesion = cursor.fetchone()
            if not sesion:
                return jsonify({'error': 'Sesión no encontrada'}), 404

            # 👇 FIX: se agrega el JOIN con "users" para traer también el "username".
            # Antes solo se traía nombre/email desde la tabla "asistentes", y el
            # frontend (Home.jsx/Eventos.jsx) compara sesion.asistentes por
            # "username" para saber si el usuario logueado ya está registrado.
            # Como ese campo nunca llegaba, la comparación siempre fallaba y
            # el evento recién unido nunca aparecía en Home.
            cursor.execute("""
                SELECT asis.id, a.nombre, a.email, a.status, asis.hora_ingreso, u.username
                FROM asistencia_sesion asis
                JOIN asistentes a ON asis.id_asistente = a.id
                LEFT JOIN users u ON u.email = a.email
                WHERE asis.id_sesion = %s
                ORDER BY asis.hora_ingreso ASC
            """, (id_sesion,))
            asistentes = cursor.fetchall()

            cursor.execute("SELECT COUNT(*) AS total FROM asistencia_sesion WHERE id_sesion = %s", (id_sesion,))
            total = cursor.fetchone()['total']

            return jsonify({
                'capacidad': sesion['capacidad'],
                'ocupados': total,
                'disponibles': sesion['capacidad'] - total if sesion['capacidad'] else None,
                'asistentes': asistentes
            }), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@asistente_bp.route('/mis-eventos', methods=['GET'])
def mis_eventos():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE id = %s", (usuario_id,))
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': 'Usuario no encontrado'}), 404

            cursor.execute("""
                SELECT s.id, s.titulo, s.sala, s.code, s.capacidad, s.detalles,
                       s.fecha, s.hora_inicio, s.hora_fin, s.zona, s.tipo, s.created_at,
                       u.username AS organizador
                FROM asistencia_sesion asis
                JOIN asistentes a ON asis.id_asistente = a.id
                JOIN sesion s ON asis.id_sesion = s.id
                LEFT JOIN users u ON s.id_user_organizador = u.id
                WHERE a.email = %s
                ORDER BY s.fecha DESC, s.hora_inicio ASC
            """, (user['email'],))

            return jsonify([serializar(s) for s in cursor.fetchall()]), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()


@asistente_bp.route('/<int:id_asistencia>', methods=['DELETE'])
def eliminar_asistente(id_asistencia):
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT asis.id FROM asistencia_sesion asis
                JOIN sesion s ON asis.id_sesion = s.id
                WHERE asis.id = %s AND s.id_user_organizador = %s
            """, (id_asistencia, usuario_id))
            if not cursor.fetchone():
                return jsonify({'error': 'Registro no encontrado o sin permiso'}), 404

            cursor.execute("DELETE FROM asistencia_sesion WHERE id = %s", (id_asistencia,))
            db.commit()
            return jsonify({'message': 'Asistente eliminado'}), 200
    except Exception as e:
        return jsonify({'error': 'Error en la base de datos', 'detalle': str(e)}), 500
    finally:
        if db:
            db.close()