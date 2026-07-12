from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sensor_bp = Blueprint('sensor', __name__, url_prefix='/api')


# --------------------------
# GUARDAR DATOS DEL SENSOR
# --------------------------
@sensor_bp.route('/sensores', methods=['POST'])
def recibir_sensores():

    data = request.get_json()

    if not data:
        return jsonify({"error": "No se recibió JSON"}), 400

    luz = data.get("luz")
    temperatura = data.get("temperatura")
    humedad = data.get("humedad")
    location = data.get("location")

    if luz is None and temperatura is None and humedad is None:
        return jsonify({"error": "No hay datos de sensores"}), 400

    doc = {
        "luz": luz,
        "temperatura": temperatura,
        "humedad": humedad,
        "location": location,
        "timestamp": datetime.now(timezone.utc)
    }

    try:

        db = get_db()
        collection = db["datos"]

        result = collection.insert_one(doc)

        return jsonify({
            "status": "ok",
            "mensaje": "Datos guardados",
            "id": str(result.inserted_id)
        }), 201

    except Exception as e:

        return jsonify({
            "error": "Error al guardar datos",
            "detalle": str(e)
        }), 500


# --------------------------
# OBTENER TODOS LOS DATOS
# --------------------------
@sensor_bp.route("/get_data", methods=["GET"])
def get_data():

    try:

        db = get_db()
        collection = db["datos"]

        location = request.args.get("location")

        query = {}

        if location:
            query["location"] = location

        data = list(collection.find(query).sort("timestamp", -1))

        for d in data:

            d["_id"] = str(d["_id"])

            ts = d.get("timestamp")

            if isinstance(ts, datetime):

                ts_local = ts.astimezone(
                    ZoneInfo("America/Mexico_City")
                )

                d["timestamp"] = ts_local.strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(data), 200

    except Exception as e:

        return jsonify({
            "error": "Error al obtener datos",
            "detalle": str(e)
        }), 500


# --------------------------
# OBTENER ULTIMO DATO POR UBICACION
# --------------------------
@sensor_bp.route("/latest", methods=["GET"])
def latest_by_location():

    try:

        location = request.args.get("location")

        if not location:
            return jsonify({"error": "Debe enviar location"}), 400

        db = get_db()
        collection = db["datos"]

        data = collection.find_one(
    {
        "location": {
            "$regex": f"^{location}$",
            "$options": "i"
        }
    },
    sort=[("timestamp", -1)]
)

        if not data:
            return jsonify({"mensaje": "No hay datos"}), 404

        data["_id"] = str(data["_id"])

        ts = data.get("timestamp")

        if isinstance(ts, datetime):

            ts_local = ts.astimezone(
                ZoneInfo("America/Mexico_City")
            )

            data["timestamp"] = ts_local.strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(data), 200

    except Exception as e:

        return jsonify({
            "error": "Error al obtener datos",
            "detalle": str(e)
        }), 500