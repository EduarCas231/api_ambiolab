from flask import Blueprint, request, jsonify
from database import get_db_connection_usuarios
from auth import verificar_token_request
from pywebpush import webpush, WebPushException
from config import Config
import json

push_bp = Blueprint('push', __name__, url_prefix='/api/push')


@push_bp.route('/subscribe', methods=['POST'])
def subscribe():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return jsonify({'error': 'Token inválido'}), 401

    sub = request.json
    endpoint = sub.get('endpoint')
    p256dh   = sub.get('keys', {}).get('p256dh')
    auth     = sub.get('keys', {}).get('auth')

    if not all([endpoint, p256dh, auth]):
        return jsonify({'error': 'Datos de suscripción incompletos'}), 400

    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            
            cursor.execute(
                """INSERT INTO push_subscriptions (id_user, endpoint, p256dh, auth)
                   VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE id_user=%s, p256dh=%s, auth=%s""",
                (usuario_id, endpoint, p256dh, auth, usuario_id, p256dh, auth)
            )
            db.commit()
        return jsonify({'message': 'Suscripción guardada'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if db:
            db.close()


@push_bp.route('/public-key', methods=['GET'])
def get_public_key():
    return jsonify({'publicKey': Config.VAPID_PUBLIC_KEY})


def enviar_push(id_user, titulo, mensaje):
    """Envía push a TODOS los dispositivos del usuario."""
    db = get_db_connection_usuarios()
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE id_user = %s",
                (id_user,)
            )
            subs = cursor.fetchall()

        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub['endpoint'],
                        "keys": {"p256dh": sub['p256dh'], "auth": sub['auth']}
                    },
                    data=json.dumps({"titulo": titulo, "mensaje": mensaje}),
                    vapid_private_key=Config.VAPID_PRIVATE_KEY,
                    vapid_claims=Config.VAPID_CLAIMS
                )
            except WebPushException as e:
                print(f"Push error para endpoint {sub['endpoint'][:30]}...: {e}")
                # Si el endpoint ya no es válido (410 Gone), eliminarlo
                if '410' in str(e) or '404' in str(e):
                    _eliminar_suscripcion(sub['endpoint'])
    finally:
        db.close()


def _eliminar_suscripcion(endpoint):
    db = get_db_connection_usuarios()
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM push_subscriptions WHERE endpoint = %s", (endpoint,))
            db.commit()
    finally:
        db.close()
