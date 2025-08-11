from flask import Blueprint, request, jsonify
from database import get_db_connection_usuarios

notificaciones_bp = Blueprint('notificaciones', __name__)

@notificaciones_bp.route('/notificaciones', methods=['GET'])
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

@notificaciones_bp.route('/notificaciones/unread-count', methods=['GET'])
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

@notificaciones_bp.route('/notificaciones/read-all', methods=['PUT'])
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

@notificaciones_bp.route('/notificaciones/<int:id>/read', methods=['PUT'])
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

@notificaciones_bp.route('/notificaciones/<int:id>', methods=['DELETE'])
def eliminar_notificacion(id):
    db = None
    cursor = None
    try:
        db = get_db_connection_usuarios()
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

@notificaciones_bp.route('/notificaciones/visita/<int:visita_id>', methods=['DELETE'])
def eliminar_notificaciones_por_visita(visita_id):
    db = None
    cursor = None
    try:
        db = get_db_connection_usuarios()
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