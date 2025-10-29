import bcrypt
import numpy as np
from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta
from decouple import config
from sentence_transformers import SentenceTransformer

SECRET_KEY = config("SECRET_KEY", default="supersecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

embed_model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

embedding_cache = {}

def get_query_embedding(text: str) -> np.ndarray:
    return embed_model.encode(text, normalize_embeddings=True)

def cosine_similarity(a, b):
    return float(np.dot(a, b))

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

def create_jwt_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_jwt_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except ExpiredSignatureError:
        raise JWTError("Token expired")
    except JWTError:
        raise JWTError("Invalid token")
