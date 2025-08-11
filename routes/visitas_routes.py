from flask import Blueprint, request, jsonify
from database import get_db_connection_usuarios, get_db_connection_visitas
import random
import string
import io
import base64
import qrcode
from datetime import datetime

visitas_bp = Blueprint('visitas', __name__)

# -------------------- VISITAS AMBIOLAB --------------------
@visitas_bp.route('/visitam', methods=['GET'])
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

@visitas_bp.route('/visitam', methods=['POST'])
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

@visitas_bp.route('/visitam/<int:id>', methods=['PUT'])
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
        escaneado = data.get('escaneado')
        fecha_escaneo = data.get('fecha_escaneo')

        db = get_db_connection_usuarios()
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

@visitas_bp.route('/visitam/<int:id>', methods=['DELETE'])
def eliminar_visita(id):
    db = None
    try:
        db = get_db_connection_usuarios()
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

@visitas_bp.route('/visitam/<int:id>', methods=['GET'])
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

@visitas_bp.route('/visitam/codigo/<string:codigo>', methods=['GET'])
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

@visitas_bp.route('/visitam/<int:id>/escaneado', methods=['PATCH'])
def marcar_visita_escaneada(id):
    db = None
    try:
        data = request.json
        escaneado = data.get('escaneado', True)
        fecha_escaneo = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db = get_db_connection_usuarios()
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

# -------------------- VISITAS LABSA --------------------
@visitas_bp.route('/visitas/codigo/<string:codigo>', methods=['GET'])
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

@visitas_bp.route('/visitas', methods=['GET'])
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

@visitas_bp.route('/visitas', methods=['POST'])
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

@visitas_bp.route('/visitas/<int:id>', methods=['PUT'])
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

@visitas_bp.route('/visitas/<int:id>', methods=['DELETE'])
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

@visitas_bp.route('/visitas/<int:id>', methods=['GET'])
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