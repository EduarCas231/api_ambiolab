from flask import Blueprint, request, jsonify
from database import get_db_connection_usuarios
from auth import verificar_token_request

pedidos_bp = Blueprint('pedidos', __name__)

@pedidos_bp.route('/pedidos', methods=['GET'])
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

@pedidos_bp.route('/pedidos/<int:id_pedidos>', methods=['GET'])
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

@pedidos_bp.route('/pedidos', methods=['POST'])
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

@pedidos_bp.route('/pedidos/<int:id_pedidos>', methods=['PUT'])
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

@pedidos_bp.route('/pedidos/<int:id_pedidos>', methods=['DELETE'])
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