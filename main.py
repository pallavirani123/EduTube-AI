# main.py
from fastapi import FastAPI, HTTPException, Depends, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import numpy as np
import requests
from jose import jwt, JWTError
from decouple import config
from sentence_transformers import SentenceTransformer
import random
import itertools
from models import UserCreate


from database import feedback_collection, bookmarks_collection, history_collection, user_collection
from utils import (
    get_query_embedding,
    cosine_similarity,
    hash_password,
    verify_password,
    create_jwt_token,
    decode_jwt_token,
    embedding_cache,
)


# ---------------- CONFIG ----------------
YOUTUBE_API_KEY= config("YOUTUBE_API_KEY")

SECRET_KEY = config("SECRET_KEY", default="supersecretkey")
ALGORITHM = "HS256"

if not YOUTUBE_API_KEY:
    raise RuntimeError("Missing YOUTUBE_API_KEY in .env")

app = FastAPI(title="EduTube AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login_user")

embedder = SentenceTransformer("all-MiniLM-L6-v2")


# ---------------- AUTH ----------------
@app.post("/register_user")
def register_user(user: UserCreate):
    """Registers a new user."""
    if user_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw = hash_password(user.password)
    user_doc = {
        "name": user.name,
        "email": user.email,
        "password": hashed_pw,
        "created_at": datetime.utcnow(),
    }
    user_collection.insert_one(user_doc)
    return {"message": "✅ User registered successfully"}


@app.post("/login_user")
def login_user(email: str = Form(...), password: str = Form(...)):
    """Logs in an existing user."""
    user = user_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt_token({"sub": email})
    return {"message": "✅ Login successful", "access_token": token}


def get_current_user(token: str = Depends(oauth2_scheme)):
    """Extracts and validates current user from JWT."""
    try:
        payload = decode_jwt_token(token)
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = user_collection.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Token verification failed")


# ---------------- YOUTUBE ----------------
def search_youtube(query, max_results=10, video_duration=None, published_after=None, page_token=None):
    """Search YouTube API for educational videos."""
    print(f"\n🔍 Searching YouTube for: {query}")
    print(f"🧩 Duration: {video_duration}, Published after: {published_after}, Page token: {page_token}")
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
        "order":random.choice(["relevance","viewCount","date"])
    }
    
    if video_duration:
        params["videoDuration"] = video_duration

    if published_after:
        mapping = {
            "last_hour": datetime.utcnow() - timedelta(hours=1),
            "today": datetime.utcnow() - timedelta(days=1),
            "this_week": datetime.utcnow() - timedelta(weeks=1),
            "this_month": datetime.utcnow() - timedelta(days=30),
            "this_year": datetime.utcnow() - timedelta(days=365),
        }
        if published_after in mapping:
            params["publishedAfter"] = mapping[published_after].isoformat("T") + "Z"

    if page_token:
        params["pageToken"] = page_token
    try:
        res = requests.get(url, params=params)
        print(f"📡 YouTube API status: {res.status_code}")
        print(f"📦 Response preview: {res.text[:500]}")
        res.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f" youtube api error:{e}")
        if res.status_code==403:
            params.pop("publishedAfter", None)
            params["order"]="relevance"
            res=requests.get(url,params=params)
            res.raise_for_status()
    data = res.json()
    seen_titles = set()
    videos = []
    for item in data.get("items", []):
        title = item["snippet"]["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        vid = item["id"]["videoId"]
        videos.append({
            "video_id": vid,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
    random.shuffle(videos)
    return videos, data.get("nextPageToken"), data.get("prevPageToken")


@app.get("/recommend/youtube")
def recommend_youtube(
    query: str,
    max_results: int = 5,
    video_duration: Optional[str] = Query(None),
    published_after: Optional[str] = Query(None),
    user_email:Optional[str]=Query(None),
):
    """Generates semantic + personalized YouTube recommendations."""
    current_user = user_email or "guest"
    videos, next_page, prev_page = search_youtube(query, max_results * 5, video_duration, published_after)

    query_emb = embedding_cache.get(query)
    if query_emb is None:
        query_emb = get_query_embedding(query)
        embedding_cache[query] = query_emb

    for v in videos:
        text = f"{v['title']} {v.get('description', '')}".strip()
        emb = embedding_cache.get(text)
        if emb is None:
            emb = get_query_embedding(text)
            embedding_cache[text] = emb
        v["score"] = cosine_similarity(query_emb, emb)

    liked = list(feedback_collection.find({"user_id": current_user, "feedback": "like"}))
    disliked = list(feedback_collection.find({"user_id": current_user, "feedback": "dislike"}))
    bookmarks = list(bookmarks_collection.find({"user_id": current_user}))

    liked_emb = [np.array(v["embedding"]) for v in liked if "embedding" in v]
    disliked_emb = [np.array(v["embedding"]) for v in disliked if "embedding" in v]
    bookmark_emb = [np.array(v["embedding"]) for v in bookmarks if "embedding" in v]

    for rec in videos:
        if rec["title"] in embedding_cache:
            rec_embed = embedding_cache[rec["title"]]
        else:
            rec_embed = get_query_embedding(rec["title"])
            embedding_cache[rec["title"]] = rec_embed

        if liked_emb:
            rec["score"] += 0.3 * max(cosine_similarity(rec_embed, e) for e in liked_emb)
        if bookmark_emb:
            rec["score"] += 0.2 * max(cosine_similarity(rec_embed, e) for e in bookmark_emb)
        if disliked_emb:
            rec["score"] -= 0.4 * max(cosine_similarity(rec_embed, e) for e in disliked_emb)

    ranked = sorted(videos, key=lambda x: x["score"], reverse=True)[:max_results]
    return {"videos": ranked, "next_page_token": next_page, "prev_page_token": prev_page}


# ---------------- FEEDBACK, HISTORY, BOOKMARKS ----------------
@app.post("/feedback")
def feedback(user_id: str, video_id: str, title: str, url: str, feedback: str):
    emb = get_query_embedding(title).tolist()
    feedback_collection.insert_one({
        "user_id": user_id,
        "video_id": video_id,
        "title": title,
        "url": url,
        "feedback": feedback,
        "embedding": emb,
        "timestamp": datetime.utcnow(),
    })
    return {"message": "Feedback saved"}


@app.post("/bookmarks/add")
def add_bookmark(user_id: str, video_id: str, title: str, url: str):
    if bookmarks_collection.find_one({"user_id": user_id, "video_id": video_id}):
        return {"message": "Already bookmarked"}
    emb = get_query_embedding(title).tolist()
    bookmarks_collection.insert_one({
        "user_id": user_id,
        "video_id": video_id,
        "title": title,
        "url": url,
        "embedding": emb,
        "timestamp": datetime.utcnow(),
    })
    return {"message": "Bookmarked!"}


@app.post("/history/add")
def add_history(user_id: str, video_id: str, title: str, url: str):
    history_collection.insert_one({
        "user_id": user_id,
        "video_id": video_id,
        "title": title,
        "url": url,
        "timestamp": datetime.utcnow(),
    })
    return {"message": "History added"}

# ---------------- FETCH ROUTES ----------------

@app.get("/feedback/likes")
def get_liked_videos(user_id: str):
    likes = list(feedback_collection.find({"user_id": user_id, "feedback": "like"}))
    for l in likes:
        l["_id"] = str(l["_id"])
    return likes


@app.get("/bookmarks/get")
def get_bookmarks(user_id: str):
    bookmarks = list(bookmarks_collection.find({"user_id": user_id}))
    for b in bookmarks:
        b["_id"] = str(b["_id"])
    return bookmarks


@app.get("/history/get")
def get_history(user_id: str, limit: int = 20):
    history = list(history_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit))
    for h in history:
        h["_id"] = str(h["_id"])
    return history


@app.delete("/history/clear")
def clear_history(user_id: str):
    history_collection.delete_many({"user_id": user_id})
    return {"message": "History cleared"}


@app.delete("/bookmarks/remove")
def remove_bookmark(user_id: str, video_id: str):
    bookmarks_collection.delete_one({"user_id": user_id, "video_id": video_id})
    return {"message": "Bookmark removed"}

