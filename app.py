from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from routes.auth_routes import auth_bp
from routes.sesion import sesion_bp
from routes.asistente import asistente_bp
from routes.push_routes import push_bp
from routes.sse import sse_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config['JWT_SECRET_KEY'] = Config.SECRET_KEY
    JWTManager(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(sesion_bp)
    app.register_blueprint(asistente_bp)
    app.register_blueprint(push_bp)
    app.register_blueprint(sse_bp)
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
