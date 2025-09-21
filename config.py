import os

class Config:
    SECRET_KEY = 'AdminTics222310'
    UPLOAD_FOLDER = '/var/www/request'
    
    # Database configurations
    DB_LABSA = {
        'host': "127.0.0.1",
        'user': "adminfull",
        'password': "222310342",
        'database': "labsa",
        'port': 3308
    }
    
    DB_AMBIOLAB = {
        'host': "localhost",
        'user': "adminfull",
        'password': "222310342",
        'database': "ambiolab",
        'port': 3308    }