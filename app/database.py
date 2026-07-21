import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/ecowatts")

try:
    # Agregamos serverSelectionTimeoutMS para que no se quede colgado si no encuentra la BD
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client.get_database("ecowatts")
    # Hacemos una prueba rápida
    client.server_info() 
    print(" Conexión exitosa a MongoDB")
except Exception as e:
    print(f" Error de conexión a MongoDB: {e}")
    db = None