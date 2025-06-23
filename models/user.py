from database import get_db_connection_usuarios
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    @staticmethod
    def create(nombre, app, apm, correo, password, tipo=0):
        hashed_password = generate_password_hash(password)
        db = get_db_connection_usuarios()
        try:
            with db.cursor() as cursor:
                query = """
                    INSERT INTO users (nombre, app, apm, correo, password, tipo) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (nombre, app, apm, correo, hashed_password, tipo))
                db.commit()
                return cursor.lastrowid
        finally:
            db.close()
    
    @staticmethod
    def find_by_email(correo):
        db = get_db_connection_usuarios()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE correo = %s", (correo,))
                return cursor.fetchone()
        finally:
            db.close()
    
    @staticmethod
    def find_by_id(user_id):
        db = get_db_connection_usuarios()
        try:
            with db.cursor() as cursor:
                cursor.execute("SELECT id_user, nombre, correo, tipo FROM users WHERE id_user = %s", (user_id,))
                return cursor.fetchone()
        finally:
            db.close()