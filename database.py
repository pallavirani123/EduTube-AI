# database.py
from pymongo import MongoClient
from decouple import config

MONGO_URI = config("MONGODB_URI", default="mongodb://localhost:27017")
client = MongoClient(MONGO_URI)

db = client["edutube_ai"]
feedback_collection = db["feedback"]
bookmarks_collection = db["bookmarks"]
history_collection = db["history"]
user_collection = db["users"]
