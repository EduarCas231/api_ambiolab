from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os

# Carpeta donde se guardarán los archivos subidos
UPLOAD_FOLDER = '/var/www/request'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx'}

# Crear blueprint
upload_bp = Blueprint('upload', __name__)

# Validar extensión permitida
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ruta para subir archivo
@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró archivo'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

        # Crear carpeta si no existe
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # URL para acceder al archivo desde el frontend
        file_url = f"https://189.136.67.84/request/{filename}"

        return jsonify({'message': 'Archivo subido con éxito', 'url': file_url}), 200

    return jsonify({'error': 'Extensión de archivo no permitida'}), 400
