import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("ERROR: MONGO_URI no está configurado en las variables de entorno.")

# Conexión certificada a MongoDB Atlas
client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
    tlsCAFile=certifi.where()
)

db = client.get_database("ecowatts")

try:
    client.server_info()
    print("Conexión exitosa a MongoDB Atlas")
except Exception as e:
    print(f"Error de conexión a MongoDB: {e}")