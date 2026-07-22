import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/ecowatts")

# 1. Definimos la conexión y la base de datos a nivel global
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
db = client.get_database("ecowatts")

# 2. Hacemos la comprobación de salud dentro del try
try:
    client.server_info()
    print("Conexión exitosa a MongoDB")
except Exception as e:
    print(f"Error de conexión a MongoDB: {e}")