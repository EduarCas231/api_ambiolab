import os

class Config:
    SECRET_KEY = 'AdminTics222310'

    VAPID_PRIVATE_KEY = 'hy8oYNZkocJcdgG6hAF96QLZeffOMl2iYus8qdmobgM'
    VAPID_PUBLIC_KEY  = 'BKKWaaId0y0vdkEI-pYL5pHEiVfVKPPyLvwH4xUgUbVXjK2SMjrV8i9olxbN82TmSfc9qFJ_Gt4Av4NmVuqNEqU'
    VAPID_CLAIMS      = {'sub': 'mailto:admin@comapi.duckdns.org'}

    DB_LABSA = {
        'host': "127.0.0.1",
        'user': "adminfull",
        'password': "222310342",
        'database': "evento",
        'port': 3308
    }
