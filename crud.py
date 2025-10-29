# crud.py
from database import user_collection
from datetime import datetime

async def create_user(user):
    if user_collection.find_one({"email": user.email}):
        return {"message": "User already exists"}
    doc = {"name": user.name, "email": user.email, "password": user.password, "created_at": datetime.utcnow()}
    user_collection.insert_one(doc)
    return {"message": "User created"}

async def verify_user(email: str, password: str):
    user = user_collection.find_one({"email": email, "password": password})
    return user is not None
