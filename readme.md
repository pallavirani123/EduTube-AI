# EduTube AI

EduTube AI is a full-stack personalized YouTube learning recommender:
- Frontend: Streamlit (`app.py`)
- Backend: FastAPI (`main.py`)
- DB: MongoDB (Atlas or local)
- Semantic search: Sentence-BERT (`sentence-transformers`)

## Quick start (local)

1. Create virtualenv and activate:
   - Windows:
     ```
     python -m venv venv
     venv\Scripts\activate
     ```
   - macOS / Linux:
     ```
     python -m venv venv
     source venv/bin/activate
     ```

2. Install dependencies:

pip install -r requirements.txt


3. Create `.env` (copy from `.env.sample`) and set:

YOUTUBE_API_KEY=YOUR_YOUTUBE_API_KEY
MONGODB_URI=mongodb://localhost:27017


4. Run backend:

uvicorn main:app --reload


5. Run frontend (in another terminal):

streamlit run app.py


## Features
- Semantic recommendations via Sentence-BERT
- Personalization using likes/bookmarks/dislikes
- Watch history stored in MongoDB
- Inline playback inside Streamlit (no redirect)
