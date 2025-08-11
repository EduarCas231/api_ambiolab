import os

class Config:
    SECRET_KEY = 'AdminTics222310'
    UPLOAD_FOLDER = '/var/www/request'
    
    # Database configurations
    DB_LABSA = {
        'host': "apislab.duckdns.org",
        'user': "adminfull",
        'password': "222310342",
        'database': "labsa",
        'port': 53307
    }
    
    DB_AMBIOLAB = {
        'host': "apislab.duckdns.org",
        'user': "adminfull",
        'password': "222310342",
        'database': "ambiolab",
        'port': 53307
    }