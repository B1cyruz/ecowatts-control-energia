import os
import certifi
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/ecowatts")

# Agregamos tlsCAFile para certificar la conexión en la nube
client = MongoClient(
    MONGO_URI, 
    serverSelectionTimeoutMS=5000,
    tlsCAFile=certifi.where()
)
db = client.get_database("ecowatts")

try:
    client.server_info()
    print("Conexión exitosa a MongoDB")
except Exception as e:
    print(f"Error de conexión a MongoDB: {e}")