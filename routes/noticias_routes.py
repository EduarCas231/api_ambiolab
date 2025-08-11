from flask import Blueprint, request, jsonify
from database import get_db_connection_usuarios

noticias_bp = Blueprint('noticias', __name__)

@noticias_bp.route('/news', methods=['POST'])
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

@noticias_bp.route('/news', methods=['GET'])
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

@noticias_bp.route('/news/<int:id>', methods=['PUT'])
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

@noticias_bp.route('/news/<int:id>', methods=['DELETE'])
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