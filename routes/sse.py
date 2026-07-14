from flask import Blueprint, Response, stream_with_context
from auth import verificar_token_request
from queue import Queue, Empty
import json
import threading

sse_bp = Blueprint('sse', __name__, url_prefix='/api/sse')

# Dict de colas por usuario: { usuario_id: [Queue, Queue, ...] }
_clientes = {}
_lock = threading.Lock()


def _agregar_cliente(usuario_id):
    q = Queue(maxsize=20)
    with _lock:
        _clientes.setdefault(usuario_id, []).append(q)
    return q


def _eliminar_cliente(usuario_id, q):
    with _lock:
        if usuario_id in _clientes:
            try:
                _clientes[usuario_id].remove(q)
            except ValueError:
                pass
            if not _clientes[usuario_id]:
                del _clientes[usuario_id]


def notificar_usuario(usuario_id, tipo, datos):
    """Llamar desde cualquier blueprint para empujar un evento al cliente."""
    mensaje = f"event: {tipo}\ndata: {json.dumps(datos)}\n\n"
    with _lock:
        colas = list(_clientes.get(usuario_id, []))
    for q in colas:
        try:
            q.put_nowait(mensaje)
        except Exception:
            pass


def notificar_usuarios(ids, tipo, datos):
    """Notificar a múltiples usuarios a la vez."""
    for uid in ids:
        notificar_usuario(uid, tipo, datos)


@sse_bp.route('/stream')
def stream():
    usuario_id = verificar_token_request()
    if not usuario_id:
        return Response('Unauthorized', status=401)

    q = _agregar_cliente(usuario_id)

    def generar():
        # Heartbeat inicial para confirmar conexión
        yield ": connected\n\n"
        try:
            while True:
                try:
                    msg = q.get(timeout=25)
                    yield msg
                except Empty:
                    # Heartbeat cada 25s para mantener conexión viva
                    yield ": ping\n\n"
        except GeneratorExit:
            pass
        finally:
            _eliminar_cliente(usuario_id, q)

    return Response(
        stream_with_context(generar()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )
