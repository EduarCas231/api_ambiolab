from flask import Flask
from flask_cors import CORS
from config import Config

# Importar todos los blueprints
from routes.auth_routes import auth_bp
from routes.visitas_ambiolab import visitam_bp
from routes.visitas_labsa import visitas_bp
from routes.notificaciones import notificaciones_bp
from routes.pedidos import pedidos_bp
from routes.noticias import noticias_bp
from upload_routes import upload_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)
    
    # Registrar blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(visitam_bp, url_prefix='/visitam')
    app.register_blueprint(visitas_bp, url_prefix='/visitas')
    app.register_blueprint(notificaciones_bp, url_prefix='/notificaciones')
    app.register_blueprint(pedidos_bp, url_prefix='/pedidos')
    app.register_blueprint(noticias_bp, url_prefix='/news')
    app.register_blueprint(upload_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8000)