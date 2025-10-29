import streamlit as st
import requests
import pandas as pd
import streamlit.components.v1 as components

BACKEND_URL = "https://edutube-ai-backend.onrender.com"

# --- Page Config ---
st.set_page_config(page_title="EduTube AI", layout="wide")

# --- Custom CSS ---
st.markdown("""
    <style>
        body {
            background-color: #0e1117;
            color: white;
        }
        .title {
            font-size: 2em; font-weight: bold; margin-bottom: 10px; color: #66d9ef;
        }
        .card {
            border: 1px solid #333;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #1e222a;
        }
        .stButton>button {
            background-color: #333 !important;
            color: #fff;
            border-radius: 5px;
        }
        .stButton>button:hover {
            background-color: #007bff !important;
        }
        img {
            border-radius: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- Session Initialization ---
for key in [
    "logged_in", "user_email", "last_videos", "view",
    "last_query", "last_filters", "next_page_token",
    "prev_page_token", "watched", "access_token", "page_tokens"
]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["last_videos", "watched", "page_tokens"] else None
        if key == "logged_in": st.session_state[key] = False
        if key in ["user_email", "last_query", "access_token"]: st.session_state[key] = ""
        if key == "last_filters": st.session_state[key] = {}

# --- LOGIN PAGE ---
if not st.session_state.logged_in:
    st.markdown("<div class='title'>EduTube AI - Learn without leaving your focus zone.</div>", unsafe_allow_html=True)
    email = st.text_input("📧 Email")
    password = st.text_input("🔑 Password", type="password")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔓 Login"):
            try:
                res = requests.post(f"{BACKEND_URL}/login_user", data={"email": email, "password": password})
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.access_token = data.get("access_token", "")
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error(res.json().get("detail", "Invalid credentials."))
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        if st.button("📝 Register"):
            try:
                name = email.split("@")[0] if "@" in email else email
                res = requests.post(f"{BACKEND_URL}/register_user", json={
                    "name": name,
                    "email": email,
                    "password": password
                })
                if res.status_code == 200:
                    st.success("✅ Registered! Please log in.")
                else:
                    st.error(res.json().get("detail", "Registration failed."))
            except Exception as e:
                st.error(f"Error: {e}")

# --- MAIN APP ---
else:
    st.markdown("<div class='title'>EduTube AI - Learn without leaving your focus zone.</div>", unsafe_allow_html=True)

    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- Filters ---
    col_query, col_duration, col_upload, col_count = st.columns([4, 2, 2, 2])
    query = col_query.text_input("🔍 Search Topic", placeholder="Search educational content...")
    duration = col_duration.selectbox("⏱ Duration", ["any", "short (<4 min)", "medium (4-20 min)", "long (>20 min)"])
    upload = col_upload.selectbox("📅 Upload Date", ["any", "last hour", "today", "this week", "this month", "this year"])
    max_results = col_count.selectbox("🎞️ Number of Videos", [3, 5, 10, 15, 20, 30], index=1)

    headers = {"Authorization": f"Bearer {st.session_state.access_token}"}

    # --- Control Buttons ---
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # --- Search Button ---
    if col1.button("🔍 Search"):
        st.session_state.view = "search"
        st.session_state.last_query = query
        st.session_state.page_tokens = []
        st.session_state.last_filters = {"duration": duration, "upload": upload, "max_results": max_results}
        try:
            duration_map = {"any": None, "short (<4 min)": "short", "medium (4-20 min)": "medium", "long (>20 min)": "long"}
            upload_map = {"any": None, "last hour": "last_hour", "today": "today", "this week": "this_week",
                          "this_month": "this_month", "this_year": "this_year"}

            params = {
                "query": query,
                "max_results": max_results,
                "user_email": st.session_state.user_email
            }
            if duration_map[duration]:
                params["video_duration"] = duration_map[duration]
            if upload_map[upload]:
                params["published_after"] = upload_map[upload]

            res = requests.get(f"{BACKEND_URL}/recommend/youtube", params=params, headers=headers)
            res.raise_for_status()
            data = res.json()
            st.session_state.last_videos = data.get("videos", [])
            if data.get("next_page_token"):
                st.session_state.page_tokens = [data.get("next_page_token")]
        except Exception as e:
            st.error(f"Search failed: {e}")
            st.session_state.last_videos = []

    # --- Navigation Buttons ---
    if col2.button("❤️ Likes"):
        st.session_state.view = "liked"
    if col3.button("🔖 Bookmarks"):
        st.session_state.view = "bookmarks"
    if col4.button("📜 History"):
        st.session_state.view = "history"

    # --- ✅ REFRESH BUTTON ---
    if col5.button("🔄 Refresh") and st.session_state.last_query:
        try:
            f = st.session_state.last_filters
            duration_map = {"any": None, "short (<4 min)": "short", "medium (4-20 min)": "medium", "long (>20 min)": "long"}
            upload_map = {"any": None, "last hour": "last_hour", "today": "today", "this week": "this_week",
                          "this_month": "this_month", "this_year": "this_year"}

            params = {
                "query": st.session_state.last_query,
                "max_results": f["max_results"],
                "user_email": st.session_state.user_email
            }
            if duration_map[f["duration"]]:
                params["video_duration"] = duration_map[f["duration"]]
            if upload_map[f["upload"]]:
                params["published_after"] = upload_map[f["upload"]]

            # ✅ Use next page token for new results
            if st.session_state.page_tokens:
                params["page_token"] = st.session_state.page_tokens.pop(0)
            else:
               st.info("Fetching a fresh random order set...")
            res = requests.get(f"{BACKEND_URL}/recommend/youtube", params=params, headers=headers)
            res.raise_for_status()
            data = res.json()
            new_videos = data.get("videos", [])
            next_token = data.get("next_page_token")
            if next_token:
                st.session_state.page_tokens.append(next_token)

            if new_videos and new_videos != st.session_state.last_videos:
                st.session_state.last_videos=new_videos
                st.info("New recommendations loaded")
            else:
                st.success(" No new recommendations loaded!")
        except Exception as e:
            st.error(f"Refresh failed: {e}")

    # --- 📤 EXPORT BOOKMARKS ---
    if col6.button("📤 Export Bookmarks"):
        try:
            bookmarks = requests.get(
                f"{BACKEND_URL}/bookmarks/get",
                params={"user_id": st.session_state.user_email},
                headers=headers
            ).json()
            if bookmarks:
                df = pd.DataFrame(bookmarks)
                st.download_button(
                    "📥 Download CSV",
                    data=df.to_csv(index=False),
                    file_name="bookmarks.csv",
                    mime="text/csv"
                )
            else:
                st.info("No bookmarks to export.")
        except Exception as e:
            st.error(f"Export failed: {e}")

    st.markdown("---")

    # --- VIEW SECTION ---
    view = st.session_state.view

    if view == "search":
        if not st.session_state.last_videos:
            st.info("🔍 Use the search bar above to find recommended YouTube videos.")
        else:
            for i, video in enumerate(st.session_state.last_videos):
                with st.container():
                    st.markdown("<div class='card'>", unsafe_allow_html=True)
                    st.subheader(video["title"])
                    st.markdown(f"**Score:** `{video.get('score', 0):.2f}`")

                    thumbnail_url = f"https://img.youtube.com/vi/{video['video_id']}/0.jpg"
                    embed_url = f"https://www.youtube.com/embed/{video['video_id']}"

                    if video["video_id"] not in st.session_state.watched:
                        st.image(thumbnail_url, width=400)
                        if st.button("▶️ Watch", key=f"watch_{i}"):
                            st.session_state.watched.append(video["video_id"])
                            try:
                                requests.post(f"{BACKEND_URL}/history/add", params={
                                    "user_id": st.session_state.user_email,
                                    "video_id": video["video_id"],
                                    "title": video["title"],
                                    "url": video["url"]
                                }, headers=headers)
                            except Exception as e:
                                st.error(f"History save failed: {e}")
                            st.rerun()
                    else:
                        components.iframe(embed_url, width=640, height=360)

                    colA, colB, colC = st.columns(3)
                    with colA:
                        if st.button("👍 Like", key=f"like_{i}"):
                            requests.post(f"{BACKEND_URL}/feedback", params={
                                "user_id": st.session_state.user_email,
                                "video_id": video["video_id"],
                                "title": video["title"],
                                "url": video["url"],
                                "feedback": "like"
                            }, headers=headers)
                            st.success("Liked!")
                    with colB:
                        if st.button("👎 Dislike", key=f"dislike_{i}"):
                            requests.post(f"{BACKEND_URL}/feedback", params={
                                "user_id": st.session_state.user_email,
                                "video_id": video["video_id"],
                                "title": video["title"],
                                "url": video["url"],
                                "feedback": "dislike"
                            }, headers=headers)
                            st.warning("Disliked!")
                    with colC:
                        if st.button("🔖 Bookmark", key=f"bookmark_{i}"):
                            requests.post(f"{BACKEND_URL}/bookmarks/add", params={
                                "user_id": st.session_state.user_email,
                                "video_id": video["video_id"],
                                "title": video["title"],
                                "url": video["url"]
                            }, headers=headers)
                            st.success("Bookmarked!")
                    st.markdown("</div>", unsafe_allow_html=True)


    elif view == "liked":
        st.subheader("❤️ Your Liked Videos")
        try:
            liked = requests.get(f"{BACKEND_URL}/feedback/likes", params={"user_id": st.session_state.user_email}).json()
            for video in liked:
                st.markdown(f"### {video['title']}")
                components.iframe(f"https://www.youtube.com/embed/{video['video_id']}", width=640, height=360)
        except Exception as e:
            st.error(f"Failed to fetch likes: {e}")

    elif view == "bookmarks":
        st.subheader("🔖 Your Bookmarks")
        try:
            bookmarks = requests.get(f"{BACKEND_URL}/bookmarks/get", params={"user_id": st.session_state.user_email}).json()
            for bm in bookmarks:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"### {bm['title']} — Score: `{bm.get('score', 0):.2f}`")
                    components.iframe(f"https://www.youtube.com/embed/{bm['video_id']}", width=640, height=360)
                with col2:
                    if st.button("🗑️ Remove", key=f"remove_bm_{bm['video_id']}"):
                        requests.delete(f"{BACKEND_URL}/bookmarks/remove", params={
                            "user_id": st.session_state.user_email,
                            "video_id": bm["video_id"]
                        })
                        st.rerun()
        except Exception as e:
            st.error(f"Failed to fetch bookmarks: {e}")

    elif view == "history":
        st.subheader("📜 Viewing History")
        try:
            history = requests.get(f"{BACKEND_URL}/history/get", params={"user_id": st.session_state.user_email, "limit": 20}).json()
            for idx, item in enumerate(history, 1):
                st.markdown(f"### {idx}. {item['title']} — Score: `{item.get('score', 0):.2f}`")
                components.iframe(f"https://www.youtube.com/embed/{item['video_id']}", width=640, height=360)

            if st.button("🗑️ Clear History"):
                requests.delete(f"{BACKEND_URL}/history/clear", params={"user_id": st.session_state.user_email})
                st.success("History cleared!")
                st.rerun()
        except Exception as e:
            st.error(f"Failed to fetch history: {e}")
