# FLUJO DE LA NUEVA ESTRUCTURA:

# 1. api_structure.py (PRINCIPAL)
from routes.visitas_ambiolab import visitam_bp
app.register_blueprint(visitam_bp, url_prefix='/visitam')

# 2. routes/visitas_ambiolab.py (ENDPOINTS)
visitam_bp = Blueprint('visitam_routes', __name__)

@visitam_bp.route('', methods=['GET'])  # Se convierte en /visitam/
@visitam_bp.route('/<int:id>', methods=['GET'])  # Se convierte en /visitam/123

# 3. RESULTADO FINAL:
# /visitam/ → obtener_visitas_filtradas()
# /visitam/123 → obtener_visita_por_id(123)
# /visitam/codigo/ABC123 → obtener_visita_por_codigo('ABC123')