# Estructura de API Modular

## Estructura de archivos:
```
/opt/flask_app/
├── api_structure.py          # Aplicación principal
├── config.py                 # Configuraciones
├── database.py              # Conexiones BD
├── models/                  # Modelos de datos
│   ├── __init__.py
│   └── user.py
├── services/                # Lógica de negocio
│   ├── __init__.py
│   └── auth_service.py
└── routes/                  # Endpoints organizados
    ├── __init__.py
    ├── auth_routes.py       # /auth/*
    ├── visitas_ambiolab_routes.py  # /visitam/*
    ├── visitas_labsa_routes.py     # /visitas/*
    ├── notificaciones_routes.py    # /notificaciones/*
    ├── pedidos_routes.py           # /pedidos/*
    └── noticias_routes.py          # /news/*
```

## Para usar:
```bash
python3 api_structure.py
```

## Endpoints disponibles:
- `/auth/register` - POST
- `/auth/login` - POST  
- `/auth/verify` - GET
- `/visitam/*` - Visitas Ambiolab
- `/visitas/*` - Visitas Labsa
- `/notificaciones/*` - Sistema notificaciones
- `/pedidos/*` - Gestión pedidos
- `/news/*` - Gestión noticias

## Ventajas:
- ✅ Código separado por responsabilidad
- ✅ Fácil mantenimiento
- ✅ Escalable
- ✅ Reutilizable para otras APIs