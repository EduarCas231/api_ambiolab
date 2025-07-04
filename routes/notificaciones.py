from flask import Blueprint, jsonify
from database import get_db_connection_usuarios

notificaciones_bp = Blueprint('notificaciones', __name__)

@notificaciones_bp.route('', methods=['GET'])
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

@notificaciones_bp.route('/unread-count', methods=['GET'])
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

@notificaciones_bp.route('/read-all', methods=['PUT'])
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

@notificaciones_bp.route('/<int:id>/read', methods=['PUT'])
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