import pymysql
from config import Config

def get_db_connection_usuarios():
    return pymysql.connect(
        **Config.DB_AMBIOLAB,
        cursorclass=pymysql.cursors.DictCursor
    )

def get_db_connection_visitas():
    return pymysql.connect(
        **Config.DB_LABSA,
        cursorclass=pymysql.cursors.DictCursor
    )