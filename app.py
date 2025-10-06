import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression
import sqlite3
from datetime import datetime, date
from textblob import TextBlob
import re
import random

# ---------------------------
# DB Setup
# ---------------------------
def init_db():
    conn = sqlite3.connect("user_data.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id TEXT PRIMARY KEY, name TEXT, field TEXT,
                 hours_per_day REAL, distractions TEXT,
                 streak_days INTEGER, badges TEXT,
                 last_updated TEXT, total_hours REAL)''')

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
                 user_id TEXT, log_date TEXT, distraction_free INTEGER,
                 hours REAL, exercise INTEGER, diet INTEGER, early_morning INTEGER)''')

    conn.commit()
    return conn

# ---------------------------
# ML Helpers
# ---------------------------
def recommend_goal(interests, df):
    interest_vector = np.zeros(len(df.columns[1:]))
    for interest in interests:
        if interest in df.columns[1:]:
            interest_vector[df.columns[1:].index(interest)] = 1
    similarities = cosine_similarity([interest_vector], df.iloc[:, 1:])[0]
    top_idx = np.argmax(similarities)
    return df['field'][top_idx]

def predict_progress(hours_per_day, total_hours=0):
    X = np.array([[1], [2], [3], [4], [5], [6], [8]]).reshape(-1, 1)
    y = np.array([10000/1, 10000/2, 10000/3, 10000/4, 10000/5, 10000/6, 10000/8])
    model = LinearRegression().fit(X, y)
    days_remaining = model.predict(np.array([[hours_per_day]]))[0] - (total_hours / max(1, hours_per_day))
    months = max(0, round(days_remaining / 30, 1))
    years = round(months / 12, 1)
    return months, years, total_hours + (hours_per_day * 30)

def detect_distractions(text):
    if text.lower() == "none":
        return False
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity
    keywords = ['social media', 'gaming', 'scrolling', 'tv', 'procrastinate']
    has_keywords = any(re.search(k, text.lower()) for k in keywords)
    return sentiment < 0 or has_keywords

# ---------------------------
# Stage System
# ---------------------------
def check_stage_progress(hours, distraction_free, exercise, diet, early_morning, streak_days):
    if hours >= 2 and distraction_free and streak_days >= 15:
        return "🥉 Silver", True, "✅ Silver achieved: 15 days, 2 hrs/day, no distractions!"
    if hours >= 4 and distraction_free and exercise and diet and streak_days >= 30:
        return "🥈 Platinum", True, "🏆 Platinum: 30 days, 4 hrs/day, + exercise + diet!"
    if hours >= 6 and distraction_free and exercise and early_morning and streak_days >= 60:
        return "🥇 Gold", True, "🔥 Gold unlocked: 60 days, 6 hrs early morning + no distractions + exercise!"
    return None, False, "⏳ Keep building your streak and meet the conditions!"

# ---------------------------
# DB Helpers
# ---------------------------
def log_daily_entry(conn, user_id, distraction_free, hours, exercise, diet, early_morning):
    today = date.today().isoformat()
    c = conn.cursor()

    c.execute("SELECT * FROM logs WHERE user_id=? AND log_date=?", (user_id, today))
    row = c.fetchone()
    if row:
        return  # already logged today

    c.execute("INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?, ?)",
              (user_id, today, int(distraction_free), hours, int(exercise), int(diet), int(early_morning)))

    # Update streak
    c.execute("SELECT streak_days, last_updated, total_hours FROM users WHERE user_id=?", (user_id,))
    user = c.fetchone()

    streak_days, last_update, total_hours = 0, None, 0
    if user:
        streak_days, last_update, total_hours = user[0], user[1], user[2]
    last_update = last_update or ""
    if last_update != today and distraction_free:
        streak_days += 1
    total_hours += hours

    c.execute("""INSERT OR REPLACE INTO users
                 (user_id, name, field, hours_per_day, distractions, streak_days, badges, last_updated, total_hours)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (user_id, "Anonymous", "Unknown", hours, "", streak_days, "", today, total_hours))
    conn.commit()

def get_user(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if row:
        return {
            "user_id": row[0], "name": row[1], "field": row[2],
            "hours_per_day": row[3], "distractions": row[4],
            "streak_days": row[5], "badges": row[6],
            "last_updated": row[7], "total_hours": row[8]
        }
    return None

def get_logs(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT log_date, distraction_free, hours, exercise, diet, early_morning FROM logs WHERE user_id=?", (user_id,))
    return c.fetchall()

# ---------------------------
# Motivational Quotes
# ---------------------------
quotes = [
    "The journey of a thousand miles begins with one step. - Lao Tzu",
    "Success is the sum of small efforts repeated day in and day out. - Robert Collier",
    "You are never too old to set another goal or to dream a new dream. - C.S. Lewis"
]

# ---------------------------
# Streamlit App
# ---------------------------
def main():
    st.set_page_config(page_title="The Brain App", page_icon="🧠", layout="wide")
    st.title("🧠 The Brain That Helps You Use Your Brain")
    st.markdown("**Your ML-powered coach for goals, streaks, and transformation.**")

    conn = init_db()

    # Sidebar
    st.sidebar.header("Profile")
    user_id = st.sidebar.text_input("User ID", "syedmra102")
    st.sidebar.write(random.choice(quotes))

    col1, col2 = st.columns(2)

    with col1:
        st.header("Daily Log")
        field = st.text_input("Your Goal Field", "Programming")
        hours_today = st.slider("Hours worked today", 0, 12, 2)
        distraction_text = st.text_area("Distractions today", "None")
        exercise = st.checkbox("Did you exercise 1 hr today?")
        diet = st.checkbox("Maintained a healthy diet?")
        early_morning = st.checkbox("Worked early morning (6+ hrs)?")

        if st.button("Analyze & Save Today"):
            is_distracted = detect_distractions(distraction_text)
            distraction_free = not is_distracted

            log_daily_entry(conn, user_id, distraction_free, hours_today, exercise, diet, early_morning)
            user = get_user(conn, user_id)

            # Stage check
            stage, passed, msg = check_stage_progress(hours_today, distraction_free, exercise, diet, early_morning, user["streak_days"])
            if passed:
                st.balloons()
                st.success(msg)
            else:
                st.info(msg)

    with col2:
        st.header("Progress")
        user = get_user(conn, user_id)
        if user:
            st.write(f"📊 Streak: {user['streak_days']} days")
            st.write(f"⏱ Total Hours: {user['total_hours']:.1f}")

            logs = get_logs(conn, user_id)
            if logs:
                df = pd.DataFrame(logs, columns=["Date", "Distraction-Free", "Hours", "Exercise", "Diet", "Early Morning"])
                df["Date"] = pd.to_datetime(df["Date"])
                st.line_chart(df.set_index("Date")[["Hours"]])
                st.write("### Log History")
                st.dataframe(df.sort_values("Date", ascending=False))
        else:
            st.info("Log your first day to see progress.")

if __name__ == "__main__":
    main()
