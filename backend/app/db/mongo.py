"""MongoDB connection via PyMongo — stub.

Client is only created if MONGO_URI is set.
"""

from pymongo import MongoClient
from app.config import Config

client = None
db = None

if Config.MONGO_URI:
    client = MongoClient(Config.MONGO_URI)
    db = client.get_default_database()
