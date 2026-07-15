import threading
import time
from datetime import datetime, timedelta
from database import get_db_connection_usuarios
from routes.push_routes import enviar_push

INTERVALO_SEGUNDOS = 30  


def _hora_completa(fecha, hora):
    """Combina una columna DATE (fecha) con una columna TIME (hora, que
    pymysql devuelve como timedelta) en un datetime completo comparable."""
    return datetime.combine(fecha, datetime.min.time()) + hora


def _destinatarios(cursor, id_sesion, id_organizador):
    cursor.execute("""
        SELECT DISTINCT u.id FROM asistencia_sesion asis
        JOIN asistentes a ON asis.id_asistente = a.id
        JOIN users u ON u.email = a.email
        WHERE asis.id_sesion = %s
    """, (id_sesion,))
    ids = {row['id'] for row in cursor.fetchall()}
    ids.add(id_organizador)
    return ids


def _revisar_sesiones():
    
    db = None
    try:
        db = get_db_connection_usuarios()
        with db.cursor() as cursor:
            ahora = datetime.now()

            cursor.execute("""
                SELECT id, titulo, sala, fecha, hora_inicio, id_user_organizador,
                       notif_5min_enviada
                FROM sesion
                WHERE fecha IS NOT NULL AND hora_inicio IS NOT NULL
                  AND notif_5min_enviada = 0
            """)
            sesiones = cursor.fetchall()

            for s in sesiones:
                inicio = _hora_completa(s['fecha'], s['hora_inicio'])

                if inicio - timedelta(minutes=5) <= ahora < inicio:
                    destinatarios = _destinatarios(cursor, s['id'], s['id_user_organizador'])
                    for uid in destinatarios:
                        enviar_push(uid, f'⏰ {s["titulo"]} empieza en 5 min', f'En {s["sala"] or "su sala"}.')
                    cursor.execute("UPDATE sesion SET notif_5min_enviada = 1 WHERE id = %s", (s['id'],))
                    db.commit()
                elif ahora >= inicio:
                    
                    cursor.execute("UPDATE sesion SET notif_5min_enviada = 1 WHERE id = %s", (s['id'],))
                    db.commit()
    except Exception as e:
        print(f'[scheduler] Error revisando sesiones: {e}')
    finally:
        if db:
            db.close()


def iniciar_scheduler():
    def loop():
        while True:
            _revisar_sesiones()
            time.sleep(INTERVALO_SEGUNDOS)

    hilo = threading.Thread(target=loop, daemon=True)
    hilo.start()