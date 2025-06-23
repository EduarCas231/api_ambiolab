import os

class Config:
    SECRET_KEY = 'AdminTics222310'
    UPLOAD_FOLDER = '/var/www/request'
    
    # Configuración de base de datos Ambiolab
    DB_AMBIOLAB = {
        'host': "189.136.70.8",
        'user': "adminfull",
        'password': "222310342",
        'database': "ambiolab",
        'port': 53307
    }
    
    # Configuración de base de datos Labsa
    DB_LABSA = {
        'host': "189.136.67.84",
        'user': "AdminTics",
        'password': "AdminTics0012",
        'database': "labsa"
    }