from flask import Flask
from flask_cors import CORS
from config import Config

# Import blueprints
from routes.auth_routes import auth_bp
from routes.pedidos_routes import pedidos_bp
from routes.noticias_routes import noticias_bp
from routes.visitas_routes import visitas_bp
from routes.notificaciones_routes import notificaciones_bp
from routes.ambiolab_routes import ambiolab_bp
from upload_routes import upload_bp

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configuration
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(noticias_bp)
    app.register_blueprint(visitas_bp)
    app.register_blueprint(notificaciones_bp)
    app.register_blueprint(ambiolab_bp)
    app.register_blueprint(upload_bp)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)