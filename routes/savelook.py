from flask import Blueprint, request, jsonify
from database import get_db_connection_mongo
import smtplib
import random
import string
import base64
from bson import ObjectId
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from email_config import EMAIL_CONFIG

savelook_bp = Blueprint('savelook', __name__)

@savelook_bp.route('/up_user', methods=['POST'])
def guardar_look():
    try:
        data = request.json

        client = get_db_connection_mongo()
        db = client.savelook  
        collection = db.usuarios

        
        imagen_bytes = None
        if data.get('imagen_look'):
            try:
                
                imagen_base64 = data.get('imagen_look')
                if ',' in imagen_base64:
                    imagen_base64 = imagen_base64.split(',')[1]
                imagen_bytes = base64.b64decode(imagen_base64)
            except Exception:
                imagen_bytes = None

        look_doc = {
            'nombre': data.get('nombre'),
            'apellidos': data.get('apellidos'),
            'correo': data.get('correo'),
            'password': data.get('password'),
            'edad': data.get('edad'),
            'estado': data.get('estado'),
            'municipio': data.get('municipio'),
            'ciudad': data.get('ciudad'),
            'cp': data.get('cp'),
            'tipoSangre': data.get('tipoSangre'),
            'tipo_u': data.get('tipo_u'),
            'id_usuario': data.get('id_usuario'),
            'descripcion_look': data.get('descripcion_look'),
            'imagen_look': imagen_bytes
        }

        result = collection.insert_one(look_doc)
        client.close()  

        return jsonify({
            'message': 'Usuario y look guardado correctamente',
            'id': str(result.inserted_id)
        }), 201

    except Exception as e:
        return jsonify({
            'error': 'Error en la base de datos',
            'detalle': str(e)
        }), 500

@savelook_bp.route('/get_users', methods=['GET'])
def obtener_usuarios():
    try:
        client = get_db_connection_mongo()
        db = client.savelook  
        collection = db.usuarios

        usuarios = list(collection.find({}, {'_id': 0}))
        
        
        for usuario in usuarios:
            if usuario.get('imagen_look') and isinstance(usuario['imagen_look'], bytes):
                usuario['imagen_look'] = base64.b64encode(usuario['imagen_look']).decode('utf-8')
        
        client.close()

        return jsonify(usuarios), 200

    except Exception as e:
        return jsonify({
            'error': 'Error al obtener los usuarios',
            'detalle': str(e)
        }), 500

@savelook_bp.route('/send_verification_code', methods=['POST'])
def enviar_codigo_verificacion():
    try:
        data = request.json
        correo = data.get('correo')
        
        if not correo:
            return jsonify({'error': 'Correo es requerido'}), 400
        
        
        codigo = ''.join(random.choices(string.digits, k=6))
        
        
        client = get_db_connection_mongo()
        db = client.savelook
        collection = db.codigos_verificacion
        
        
        collection.delete_many({'correo': correo})
        
        
        expiracion = datetime.now() + timedelta(minutes=10)
        collection.insert_one({
            'correo': correo,
            'codigo': codigo,
            'expiracion': expiracion,
            'usado': False
        })
        
        
        enviar_correo(correo, codigo)
        
        client.close()
        
        return jsonify({
            'message': 'Código de verificación enviado correctamente'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Error al enviar código de verificación',
            'detalle': str(e)
        }), 500

def enviar_correo(correo_destino, codigo):
    smtp_server = EMAIL_CONFIG['SMTP_SERVER']
    smtp_port = EMAIL_CONFIG['SMTP_PORT']
    correo_origen = EMAIL_CONFIG['EMAIL']
    password_correo = EMAIL_CONFIG['PASSWORD']
    
    mensaje = MIMEMultipart()
    mensaje['From'] = correo_origen
    mensaje['To'] = correo_destino
    mensaje['Subject'] = "Código de verificación - SaveLook"
    
    cuerpo = f"""
    Hola.
    
    Tu código de verificación para SaveLook es: {codigo}
    
    Este código expira en 10 minutos.
    
    Saludos.
    Equipo SaveLook.
    """
    
    mensaje.attach(MIMEText(cuerpo, 'plain'))
    
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(correo_origen, password_correo)
    server.send_message(mensaje)
    server.quit()

@savelook_bp.route('/verify_code', methods=['POST'])
def verificar_codigo():
    try:
        data = request.json
        correo = data.get('correo')
        codigo = data.get('codigo')
        
        if not correo or not codigo:
            return jsonify({'error': 'Correo y código son requeridos'}), 400
        
        client = get_db_connection_mongo()
        db = client.savelook
        collection = db.codigos_verificacion
        
        
        codigo_doc = collection.find_one({
            'correo': correo,
            'codigo': codigo,
            'usado': False,
            'expiracion': {'$gt': datetime.now()}
        })
        
        if not codigo_doc:
            client.close()
            return jsonify({'error': 'Código inválido o expirado'}), 400
        
        
        collection.update_one(
            {'_id': codigo_doc['_id']},
            {'$set': {'usado': True}}
        )
        
        client.close()
        
        return jsonify({
            'message': 'Código verificado correctamente',
            'correo_verificado': True
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Error al verificar código',
            'detalle': str(e)
        }), 500
        
@savelook_bp.route('/update_user', methods=['PUT'])
def update_user():
    try:
        data = request.json
        correo = data.get('correo')
        
        if not correo:
            return jsonify({'error': 'Correo es requerido para actualizar'}), 400
        
        client = get_db_connection_mongo()
        db = client.savelook
        collection = db.usuarios
        
        
        usuario_existente = collection.find_one({'correo': correo})
        if not usuario_existente:
            client.close()
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        
        campos_actualizar = {}
        campos_permitidos = ['nombre', 'apellidos', 'edad', 'estado', 'municipio', 
                           'ciudad', 'cp', 'tipoSangre', 'tipo_u', 'descripcion_look']
        
        for campo in campos_permitidos:
            if campo in data:
                campos_actualizar[campo] = data[campo]
        
        
        if 'imagen_look' in data and data['imagen_look']:
            try:
                imagen_base64 = data['imagen_look']
                if ',' in imagen_base64:
                    imagen_base64 = imagen_base64.split(',')[1]
                campos_actualizar['imagen_look'] = base64.b64decode(imagen_base64)
            except Exception:
                pass  # Ignorar si no se puede convertir
        
        
        result = collection.update_one(
            {'correo': correo},
            {'$set': campos_actualizar}
        )
        
        client.close()
        
        if result.modified_count > 0:
            return jsonify({'message': 'Usuario actualizado correctamente'}), 200
        else:
            return jsonify({'message': 'No se realizaron cambios'}), 200
            
    except Exception as e:
        return jsonify({
            'error': 'Error al actualizar usuario',
            'detalle': str(e)
        }), 500

@savelook_bp.route('/get_user/<correo>', methods=['GET'])
def obtener_usuario_por_correo(correo):
    try:
        client = get_db_connection_mongo()
        db = client.savelook
        collection = db.usuarios
        
        usuario = collection.find_one({'correo': correo}, {'_id': 0})
        client.close()
        
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        
        if usuario.get('imagen_look') and isinstance(usuario['imagen_look'], bytes):
            usuario['imagen_look'] = base64.b64encode(usuario['imagen_look']).decode('utf-8')
            
        return jsonify(usuario), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Error al obtener usuario',
            'detalle': str(e)
        }), 500

@savelook_bp.route('/delete_user/<correo>', methods=['DELETE'])
def eliminar_usuario(correo):
    try:
        client = get_db_connection_mongo()
        db = client.savelook
        collection = db.usuarios
        
        result = collection.delete_one({'correo': correo})
        client.close()
        
        if result.deleted_count > 0:
            return jsonify({'message': 'Usuario eliminado correctamente'}), 200
        else:
            return jsonify({'error': 'Usuario no encontrado'}), 404
            
    except Exception as e:
        return jsonify({
            'error': 'Error al eliminar usuario',
            'detalle': str(e)
        }), 500

@savelook_bp.route('/login', methods=['POST'])
def login_usuario():
    try:
        data = request.json
        correo = data.get('correo')
        password = data.get('password')
        
        if not correo or not password:
            return jsonify({'error': 'Correo y contraseña son requeridos'}), 400
        
        client = get_db_connection_mongo()
        db = client.savelook
        collection = db.usuarios
        
        usuario = collection.find_one({
            'correo': correo,
            'password': password
        }, {'_id': 0})
        
        client.close()
        
        if usuario:
            
            if usuario.get('imagen_look') and isinstance(usuario['imagen_look'], bytes):
                usuario['imagen_look'] = base64.b64encode(usuario['imagen_look']).decode('utf-8')
            
            return jsonify({
                'message': 'Login exitoso',
                'usuario': usuario
            }), 200
        else:
            return jsonify({'error': 'Credenciales inválidas'}), 401
            
    except Exception as e:
        return jsonify({
            'error': 'Error en el login',
            'detalle': str(e)
        }), 500


@savelook_bp.route('/location/invite', methods=['POST'])
def location_invite():
    try:
        data = request.json
        email = data.get('email')
        inviter_email = data.get('inviter_email')
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        # Verificar que el usuario invitado existe
        invitee = db.usuarios.find_one({'correo': email})
        if not invitee:
            client.close()
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        # Obtener inviter
        inviter = db.usuarios.find_one({'correo': inviter_email})
        
        # Crear invitación pendiente
        db.location_shares.update_one(
            {'inviter_id': inviter['_id'], 'invitee_email': email},
            {
                '$set': {
                    'inviter_id': inviter['_id'],
                    'inviter_email': inviter_email,
                    'invitee_email': email,
                    'invitee_id': invitee['_id'],
                    'status': 'pending',
                    'created_at': datetime.now()
                }
            },
            upsert=True
        )
        
        client.close()
        return jsonify({'success': True, 'message': 'Invitación enviada'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# GET /location/invitations - Obtener invitaciones pendientes
@savelook_bp.route('/location/invitations', methods=['GET'])
def location_invitations():
    try:
        user_email = request.args.get('user_email')
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        user = db.usuarios.find_one({'correo': user_email})
        
        invitations = list(db.location_shares.aggregate([
            {'$match': {'invitee_id': user['_id'], 'status': 'pending'}},
            {'$lookup': {'from': 'usuarios', 'localField': 'inviter_id', 'foreignField': '_id', 'as': 'inviter'}},
            {'$unwind': '$inviter'},
            {'$project': {
                '_id': {'$toString': '$_id'},
                'inviter_email': '$inviter_email',
                'inviter_name': {'$concat': ['$inviter.nombre', ' ', '$inviter.apellidos']},
                'created_at': '$created_at'
            }}
        ]))
        
        client.close()
        return jsonify({'success': True, 'invitations': invitations}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# POST /location/accept - Aceptar invitación
@savelook_bp.route('/location/accept', methods=['POST'])
def location_accept():
    try:
        data = request.json
        invitation_id = data.get('invitation_id')
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        result = db.location_shares.update_one(
            {'_id': ObjectId(invitation_id)},
            {'$set': {'status': 'accepted'}}
        )
        
        client.close()
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Invitación aceptada'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invitación no encontrada'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# POST /location/reject - Rechazar invitación
@savelook_bp.route('/location/reject', methods=['POST'])
def location_reject():
    try:
        data = request.json
        invitation_id = data.get('invitation_id')
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        result = db.location_shares.delete_one({'_id': ObjectId(invitation_id)})
        
        client.close()
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Invitación rechazada'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invitación no encontrada'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# GET /location/contacts - Obtener contactos
@savelook_bp.route('/location/contacts', methods=['GET'])
def location_contacts():
    try:
        user_email = request.args.get('user_email')
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        user = db.usuarios.find_one({'correo': user_email})
        
        contacts = list(db.location_shares.aggregate([
            {'$match': {
                '$or': [{'inviter_id': user['_id']}, {'invitee_id': user['_id']}],
                'status': 'accepted'
            }},
            {'$lookup': {'from': 'usuarios', 'localField': 'invitee_id', 'foreignField': '_id', 'as': 'invitee_user'}},
            {'$lookup': {'from': 'usuarios', 'localField': 'inviter_id', 'foreignField': '_id', 'as': 'inviter_user'}},
            {'$unwind': '$invitee_user'},
            {'$unwind': '$inviter_user'},
            {'$project': {
                '_id': {'$toString': '$_id'},
                'contact_id': {
                    '$cond': {
                        'if': {'$eq': ['$inviter_id', user['_id']]},
                        'then': {'$toString': '$invitee_id'},
                        'else': {'$toString': '$inviter_id'}
                    }
                },
                'email': {
                    '$cond': {
                        'if': {'$eq': ['$inviter_id', user['_id']]},
                        'then': '$invitee_email',
                        'else': '$inviter_email'
                    }
                },
                'nombre': {
                    '$cond': {
                        'if': {'$eq': ['$inviter_id', user['_id']]},
                        'then': '$invitee_user.nombre',
                        'else': '$inviter_user.nombre'
                    }
                },
                'apellidos': {
                    '$cond': {
                        'if': {'$eq': ['$inviter_id', user['_id']]},
                        'then': '$invitee_user.apellidos',
                        'else': '$inviter_user.apellidos'
                    }
                }
            }}
        ]))
        
        client.close()
        return jsonify({'success': True, 'contacts': contacts}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# POST /location/update - Actualizar ubicación
@savelook_bp.route('/location/update', methods=['POST'])
def location_update():
    try:
        data = request.json
        user_email = data.get('user_email')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        share_with = data.get('shareWith', [])
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        user = db.usuarios.find_one({'correo': user_email})
        share_with_ids = [ObjectId(id) for id in share_with]
        
        db.active_locations.update_one(
            {'user_id': user['_id']},
            {
                '$set': {
                    'user_id': user['_id'],
                    'latitude': latitude,
                    'longitude': longitude,
                    'shared_with': share_with_ids,
                    'timestamp': datetime.now(),
                    'expires_at': datetime.now() + timedelta(minutes=30)
                }
            },
            upsert=True
        )
        
        client.close()
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# GET /location/shared - Obtener ubicaciones compartidas
@savelook_bp.route('/location/shared', methods=['GET'])
def location_shared():
    try:
        user_email = request.args.get('user_email')
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        user = db.usuarios.find_one({'correo': user_email})
        
        locations = list(db.active_locations.aggregate([
            {
                '$match': {
                    'shared_with': user['_id'],
                    'timestamp': {'$gte': datetime.now() - timedelta(minutes=5)}
                }
            },
            {'$lookup': {'from': 'usuarios', 'localField': 'user_id', 'foreignField': '_id', 'as': 'user'}},
            {'$unwind': '$user'},
            {
                '$project': {
                    'latitude': 1,
                    'longitude': 1,
                    'timestamp': 1,
                    'userId': {'$toString': '$user_id'},
                    'userName': {'$concat': ['$user.nombre', ' ', '$user.apellidos']},
                    'userEmail': '$user.correo'
                }
            }
        ]))
        
        client.close()
        return jsonify({'success': True, 'locations': locations}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# POST /location/stop - Detener compartir
@savelook_bp.route('/location/stop', methods=['POST'])
def location_stop():
    try:
        data = request.json
        user_email = data.get('user_email')
        
        client = get_db_connection_mongo()
        db = client.savelook
        
        user = db.usuarios.find_one({'correo': user_email})
        db.active_locations.delete_one({'user_id': user['_id']})
        
        client.close()
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

