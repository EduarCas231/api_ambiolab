from flask import Blueprint
from auth import register, login, verify_token

auth_bp = Blueprint('auth', __name__)

auth_bp.add_url_rule('/register', 'register', register, methods=['POST'])
auth_bp.add_url_rule('/login', 'login', login, methods=['POST'])
auth_bp.add_url_rule('/verify', 'verify_token', verify_token, methods=['GET'])