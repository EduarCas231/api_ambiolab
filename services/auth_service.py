import jwt
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash
from config import Config
from models.user import User

class AuthService:
    @staticmethod
    def generate_token(user_id):
        payload = {
            'usuario_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=8)
        }
        return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            return payload['usuario_id']
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
    
    @staticmethod
    def authenticate_user(correo, password):
        user = User.find_by_email(correo)
        if user and check_password_hash(user['password'], password):
            return user
        return None