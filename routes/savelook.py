from flask import Blueprint, request, jsonify
from database import get_db
import bcrypt
import base64
import re
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from flask_jwt_extended import (
create_access_token,
jwt_required,
get_jwt_identity
)
from email_config import EMAIL_CONFIG

savelook_bp = Blueprint("savelook", __name__)

# -----------------------------
# UTILIDADES
# -----------------------------

def validar_correo(correo):
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, correo)

def convertir_base64(imagen):
    try:
        if 'base64,' in imagen:
            imagen = imagen.split('base64,')[1]
        return base64.b64decode(imagen)
    except:
        return None

def imagen_respuesta(img):
    if img and isinstance(img, bytes):
        return "data:image/jpeg;base64," + base64.b64encode(img).decode()
    return None

def enviar_correo_verificacion(correo, codigo):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['EMAIL']
        msg['To'] = correo
        msg['Subject'] = 'Código de verificación SaveLook'
        
        body = f"""
        <html>
        <body>
            <h2>Verificación de correo SaveLook</h2>
            <p>Tu código de verificación es:</p>
            <h1 style="color: #4CAF50;">{codigo}</h1>
            <p>Este código expira en 10 minutos.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['SMTP_SERVER'], EMAIL_CONFIG['SMTP_PORT'])
        server.starttls()
        server.login(EMAIL_CONFIG['EMAIL'], EMAIL_CONFIG['PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False


# -----------------------------
# REGISTRO
# -----------------------------

@savelook_bp.route("/register", methods=["POST"])
def register():

    data = request.json
    tipo = data.get("tipo_usuario","estudiante")

    if tipo not in ["estudiante","conductor","maestro"]:
        return jsonify({"error":"tipo_usuario debe ser: estudiante, conductor o maestro"}),400

    required = ["nombre","apellidos","edad","correo","password"]

    for r in required:
        if r not in data:
            return jsonify({"error":f"{r} requerido"}),400

    if not validar_correo(data["correo"]):
        return jsonify({"error":"Correo inválido"}),400

    db = get_db()

    if tipo == "conductor":
        collection = db.conductores
    elif tipo == "maestro":
        collection = db.maestros
    else:
        collection = db.estudiantes

    if collection.find_one({"correo":data["correo"]}):
        return jsonify({"error":"Correo ya registrado"}),400

    password = bcrypt.hashpw(data["password"].encode(),bcrypt.gensalt())

    usuario = {
        "nombre":data["nombre"],
        "apellidos":data["apellidos"],
        "edad":int(data["edad"]),
        "correo":data["correo"],
        "password":password,
        "tipo_usuario":tipo
    }

    if tipo == "conductor":
        if not data.get("placas") or not data.get("detalles_vehiculo"):
            return jsonify({"error":"placas y detalles_vehiculo requeridos para conductores"}),400
        usuario["placas"]=data["placas"]
        usuario["detalles_vehiculo"]=data["detalles_vehiculo"]

    elif tipo == "maestro":
        if not data.get("identificacion"):
            return jsonify({"error":"identificacion requerida para maestros"}),400
        usuario["identificacion"]=data["identificacion"]

    else:
        if not data.get("matricula"):
            return jsonify({"error":"matricula requerida para estudiantes"}),400
        usuario["matricula"]=data["matricula"]

    if data.get("foto"):
        foto_bytes=convertir_base64(data["foto"])
        if foto_bytes:
            usuario["foto"]=foto_bytes

    collection.insert_one(usuario)

    return jsonify({"message":"Usuario registrado exitosamente"}),201


# -----------------------------
# LOGIN JWT
# -----------------------------

@savelook_bp.route("/login",methods=["POST"])
def login():

    data=request.json

    correo=data.get("correo")
    password=data.get("password")
    tipo=data.get("tipo_usuario","estudiante")

    if not correo or not password:
        return jsonify({"error":"Correo y contraseña requeridos"}),400

    if tipo not in ["estudiante","conductor","maestro"]:
        return jsonify({"error":"tipo_usuario debe ser: estudiante, conductor o maestro"}),400

    db=get_db()

    if tipo == "conductor":
        collection = db.conductores
    elif tipo == "maestro":
        collection = db.maestros
    else:
        collection = db.estudiantes

    usuario=collection.find_one({"correo":correo})

    if not usuario:
        return jsonify({"error":"Usuario no encontrado"}),404

    if not bcrypt.checkpw(password.encode(),usuario["password"]):
        return jsonify({"error":"Contraseña incorrecta"}),401

    token=create_access_token(identity=correo)

    usuario["_id"]=str(usuario["_id"])

    del usuario["password"]

    if usuario.get("foto"):
        usuario["foto"]=imagen_respuesta(usuario["foto"])

    return jsonify({
        "token":token,
        "usuario":usuario
    })


# -----------------------------
# OBTENER USUARIO
# -----------------------------

@savelook_bp.route("/profile",methods=["GET"])
@jwt_required()
def profile():

    correo=get_jwt_identity()

    db=get_db()

    usuario=db.estudiantes.find_one({"correo":correo}) or db.conductores.find_one({"correo":correo}) or db.maestros.find_one({"correo":correo})

    if not usuario:
        return jsonify({"error":"Usuario no encontrado"}),404

    usuario["_id"]=str(usuario["_id"])

    if usuario.get("foto"):
        usuario["foto"]=imagen_respuesta(usuario["foto"])

    del usuario["password"]

    return jsonify(usuario)


# -----------------------------
# UBICACION CONDUCTOR
# -----------------------------

@savelook_bp.route("/driver/location",methods=["POST"])
@jwt_required()
def actualizar_ubicacion():

    correo=get_jwt_identity()

    data=request.json

    lat=data.get("lat")
    lng=data.get("lng")

    if lat is None or lng is None:
        return jsonify({"error":"lat y lng requeridos"}),400

    db=get_db()

    db.ubicaciones.update_one(
        {"correo": correo},
        {"$set":{
            "lat": float(lat),
            "lng": float(lng),
            "timestamp": datetime.now(timezone.utc)
        }},
        upsert=True
    )

    return jsonify({"message":"Ubicación actualizada"})


# -----------------------------
# OBTENER UBICACION BUS
# -----------------------------

@savelook_bp.route("/driver/location/<correo>",methods=["GET"])
def obtener_ubicacion(correo):

    if not validar_correo(correo):
        return jsonify({"error":"Correo inválido"}),400

    db=get_db()

    loc=db.ubicaciones.find_one({"correo":correo})

    if not loc:
        return jsonify({"error":"Ubicación no disponible"}),404

    loc["_id"]=str(loc["_id"])

    return jsonify(loc)


# -----------------------------
# RUTAS
# -----------------------------

@savelook_bp.route("/rutas",methods=["POST"])
@jwt_required()
def crear_ruta():

    correo=get_jwt_identity()

    data=request.json

    if not data.get("nombre_ruta"):
        return jsonify({"error":"nombre_ruta es requerido"}),400

    db=get_db()

    ruta={
        "nombre_ruta":data.get("nombre_ruta"),
        "correo_conductor":correo,
        "descripcion":data.get("descripcion",""),
        "paradas":data.get("paradas",[])
    }

    db.rutas.insert_one(ruta)

    return jsonify({"message":"Ruta creada"}),201


@savelook_bp.route("/rutas",methods=["GET"])
def obtener_rutas():

    db=get_db()

    rutas=[]

    for r in db.rutas.find():

        r["_id"]=str(r["_id"])

        rutas.append(r)

    return jsonify(rutas)


# -----------------------------
# VERIFICACION DE CORREO
# -----------------------------

@savelook_bp.route("/send-verification",methods=["POST"])
def enviar_codigo():

    data=request.json
    correo=data.get("correo")

    if not correo or not validar_correo(correo):
        return jsonify({"error":"Correo inválido"}),400

    codigo=str(random.randint(100000,999999))

    db=get_db()

    db.codigos_verificacion.update_one(
        {"correo":correo},
        {"$set":{
            "codigo":codigo,
            "expira":datetime.now(timezone.utc)+timedelta(minutes=10)
        }},
        upsert=True
    )

    if enviar_correo_verificacion(correo,codigo):
        return jsonify({"message":"Código enviado"})
    else:
        return jsonify({"error":"Error al enviar correo"}),500


@savelook_bp.route("/verify-code",methods=["POST"])
def verificar_codigo():

    data=request.json
    correo=data.get("correo")
    codigo=data.get("codigo")

    if not correo or not codigo:
        return jsonify({"error":"Correo y código requeridos"}),400

    db=get_db()

    registro=db.codigos_verificacion.find_one({"correo":correo})

    if not registro:
        return jsonify({"error":"Código no encontrado"}),404

    if registro["codigo"]!=str(codigo):
        return jsonify({"error":"Código incorrecto"}),400

    expira=registro["expira"]
    if not expira.tzinfo:
        expira=expira.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc)>expira:
        return jsonify({"error":"Código expirado"}),400

    db.codigos_verificacion.delete_one({"correo":correo})

    return jsonify({"message":"Código verificado","verified":True})