from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os


UPLOAD_FOLDER = '/var/www/request'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'xlsx'}


upload_bp = Blueprint('upload', __name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontró archivo'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)

       
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        
        file_url = f"https://189.136.67.84/request/{filename}"

        return jsonify({'message': 'Archivo subido con éxito', 'url': file_url}), 200

    return jsonify({'error': 'Extensión de archivo no permitida'}), 400
