# app.py
# The Brain — top-notch habit/goal/roadmap app (Streamlit)
# Designed for Streamlit Cloud. Uses SQLite for persistence, no external CSV required.

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta, date
import re
import random
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression

# -----------------------
# CONFIG & CONSTANTS
# -----------------------
DB_PATH = "brain_user_data.db"

MOTIVATIONAL_QUOTES = [
    "The journey of a thousand miles begins with one step. — Lao Tzu",
    "Success is the sum of small efforts repeated day in and day out. — Robert Collier",
    "You are never too old to set another goal or to dream a new dream. — C.S. Lewis",
    "Small daily improvements are the key to staggering long-term results.",
    "Focus on progress, not perfection."
]

# Stages mapping: stage -> required hours/day
HOUR_STAGES = {1: 2, 2: 4, 3: 6}

# Badge thresholds (days)
DISTRACTION_THRESHOLDS = {"silver": 15, "platinum": 30, "gold": 60}
MASTERY_THRESHOLDS = {"silver": (3, 15), "platinum": (6, 30), "gold": (8, 60)}
# mastery tuple: (hours_per_day_required, streak_days_required)

# keywords for distraction detection
DISTRACTION_KEYWORDS = [
    "social media", "facebook", "instagram", "tiktok", "youtube", "gaming",
    "scrolling", "procrastinate", "procrastination", "netflix", "tv", "twitter", "snapchat"
]

# -----------------------
# UTIL: Database
# -----------------------
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    # users table: basic profile and cumulative stats
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT,
            field TEXT,
            hour_stage INTEGER DEFAULT 1,
            total_hours REAL DEFAULT 0,
            streak_days INTEGER DEFAULT 0,
            badges TEXT DEFAULT '',
            last_check DATE
        )
    ''')
    # daily_entries: one row per user per date (distraction_free boolean, hours_logged)
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_entries (
            user_id TEXT,
            entry_date DATE,
            distraction_free INTEGER,
            hours_logged REAL,
            PRIMARY KEY(user_id, entry_date)
        )
    ''')
    # roadmaps (prepopulated)
    c.execute('''
        CREATE TABLE IF NOT EXISTS roadmaps (
            field TEXT PRIMARY KEY,
            starting_steps TEXT,
            month1_plan TEXT,
            uniqueness_tips TEXT
        )
    ''')
    # ensure some sample roadmaps exist
    sample_roadmaps = [
        ("Cricket", "Join a local club; build fitness; get a coach.", "Daily batting and bowling drills, fitness 4x/week.", "Develop a unique skill: accurate slower balls."),
        ("Programming", "Learn Python basics, practice coding 1 hour/day.", "Build CLI tool -> web app -> deploy to GitHub.", "Niche: ML for local problems (health / energy)."),
        ("Data Science", "Learn pandas, visualize data, load datasets from Kaggle.", "Build an end-to-end model and dashboard this month.", "Focus on explainability and real datasets."),
        ("Cybersecurity", "Learn networking basics, then OWASP web vulnerabilities.", "Practice CTF challenges, set up a home lab.", "Specialize in bug bounty or IoT security."),
        ("Music", "Daily scales and ear training.", "Compose a short track and share for feedback.", "Mix traditional sounds with modern beats.")
    ]
    for f, s, m, t in sample_roadmaps:
        c.execute("INSERT OR REPLACE INTO roadmaps (field, starting_steps, month1_plan, uniqueness_tips) VALUES (?, ?, ?, ?)",
                  (f, s, m, t))
    conn.commit()
    return conn

# -----------------------
# UTIL: Data (recommendation dataset)
# -----------------------
def get_sample_skill_df():
    # small built-in matrix where columns represent skills/interest areas
    data = {
        "field": ["Data Science", "Machine Learning", "Cybersecurity", "Cloud Computing", "Network Engineering",
                  "Cricket", "Programming", "Music", "Business", "Graphic Design"],
        "math":         [1, 1, 0, 1, 1, 0, 1, 0, 0, 0],
        "coding":       [1, 1, 0, 1, 1, 0, 1, 0, 1, 1],
        "research":     [1, 1, 0, 0, 0, 0, 1, 0, 1, 0],
        "security":     [0, 0, 1, 0, 1, 0, 0, 0, 0, 0],
        "biology":      [0, 0, 0, 0, 0, 1, 0, 1, 0, 0],
        "creativity":   [0, 0, 0, 0, 0, 0, 0, 1, 1, 1]
    }
    return pd.DataFrame(data)

# -----------------------
# BUSINESS LOGIC
# -----------------------
def recommend_goal(interests, df):
    # interests: list of strings matching column names (e.g. 'coding', 'math')
    cols = list(df.columns[1:])
    interest_vector = np.zeros(len(cols))
    for interest in interests:
        interest = interest.strip().lower()
        if interest in cols:
            idx = cols.index(interest)
            interest_vector[idx] = 1
    # if user selects no recognized interest, fallback to random field
    if interest_vector.sum() == 0:
        return random.choice(df['field'].tolist())
    similarities = cosine_similarity([interest_vector], df.iloc[:, 1:])[0]
    top_idx = int(np.argmax(similarities))
    return df['field'].iloc[top_idx]

def predict_progress(hours_per_day, total_hours=0):
    # Use a simple regression based on the 10,000-hour rule (days -> months)
    X = np.array([[1], [2], [3], [4], [5], [6], [8]]).reshape(-1, 1)
    y = np.array([10000/1, 10000/2, 10000/3, 10000/4, 10000/5, 10000/6, 10000/8])
    model = LinearRegression().fit(X, y)
    # days to mastery remaining (if hours_per_day > 0)
    if hours_per_day <= 0:
        return None, None, total_hours
    days = model.predict(np.array([[hours_per_day]]))[0]
    # subtract already invested hours converted to days at current rate
    days_remaining = max(0, days - (total_hours / hours_per_day if hours_per_day > 0 else 0))
    months = round(days_remaining / 30, 1)
    years = round(months / 12, 2)
    new_total_hours = total_hours + (hours_per_day * 30)  # add 30 days of hours to total
    return months, years, new_total_hours

def detect_distractions(text):
    if not text:
        return False
    # basic keyword + simple sentiment-like heuristic
    txt = text.lower()
    if txt.strip() in ("none", "no", "n/a"):
        return False
    # keyword check
    for kw in DISTRACTION_KEYWORDS:
        if kw in txt:
            return True
    # negative language heuristic (simple)
    negative_words = ["addicted", "can't stop", "can't focus", "waste", "wasting", "procrastinate"]
    for nw in negative_words:
        if nw in txt:
            return True
    return False

def update_badges_and_stats(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT streak_days, total_hours, hour_stage FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row:
        return []
    streak_days, total_hours, hour_stage = row
    badges = []
    # Distraction-free badges based on streak_days
    if streak_days >= DISTRACTION_THRESHOLDS["gold"]:
        badges.append("Gold (Distraction-Free)")
    elif streak_days >= DISTRACTION_THRESHOLDS["platinum"]:
        badges.append("Platinum (Distraction-Free)")
    elif streak_days >= DISTRACTION_THRESHOLDS["silver"]:
        badges.append("Silver (Distraction-Free)")
    # Mastery badges based on total_hours and stage
    # We'll use simple thresholds in MASTERY_THRESHOLDS
    for label, (req_hours, req_days) in MASTERY_THRESHOLDS.items():
        if hour_stage >= 1 and total_hours >= (req_hours * req_days):
            # e.g., if they've logged (req_hours * req_days) total hours
            if label == "gold":
                badges.append("Gold (Mastery)")
            elif label == "platinum":
                badges.append("Platinum (Mastery)")
            else:
                badges.append("Silver (Mastery)")
    # store badges
    c.execute("UPDATE users SET badges = ? WHERE user_id = ?", (",".join(badges), user_id))
    conn.commit()
    return badges

# -----------------------
# UI Helpers
# -----------------------
def get_user(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT user_id, display_name, field, hour_stage, total_hours, streak_days, badges, last_check FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        keys = ["user_id","display_name","field","hour_stage","total_hours","streak_days","badges","last_check"]
        return dict(zip(keys, row))
    return None

def create_or_update_user(conn, user_id, display_name, field):
    c = conn.cursor()
    now = date.today().isoformat()
    user = get_user(conn, user_id)
    if user:
        c.execute("UPDATE users SET display_name = ?, field = ? WHERE user_id = ?", (display_name, field, user_id))
    else:
        c.execute("INSERT INTO users (user_id, display_name, field, hour_stage, total_hours, streak_days, badges, last_check) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (user_id, display_name, field, 1, 0.0, 0, "", now))
    conn.commit()

def log_daily_entry(conn, user_id, entry_date, distraction_free, hours_logged):
    c = conn.cursor()
    # insert or replace
    c.execute("""
        INSERT OR REPLACE INTO daily_entries (user_id, entry_date, distraction_free, hours_logged)
        VALUES (?, ?, ?, ?)
    """, (user_id, entry_date, int(distraction_free), float(hours_logged)))
    # update totals / streaks
    # total hours
    c.execute("SELECT SUM(hours_logged) FROM daily_entries WHERE user_id = ?", (user_id,))
    total = c.fetchone()[0] or 0.0
    # compute streak_days: number of consecutive days up to today where distraction_free == 1
    streak = compute_streak(conn, user_id)
    c.execute("UPDATE users SET total_hours = ?, streak_days = ?, last_check = ? WHERE user_id = ?",
              (total, streak, entry_date, user_id))
    conn.commit()
    # after update, recalc badges
    return update_badges_and_stats(conn, user_id)

def compute_streak(conn, user_id):
    c = conn.cursor()
    # get last 200 days entries (safeguard)
    today = date.today()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(0, 200)]
    streak = 0
    for d in dates:
        c.execute("SELECT distraction_free FROM daily_entries WHERE user_id = ? AND entry_date = ?", (user_id, d))
        r = c.fetchone()
        if r and r[0] == 1:
            streak += 1
        else:
            break
    return streak

# -----------------------
# MAIN STREAMLIT APP
# -----------------------
def main():
    st.set_page_config(page_title="🧠 The Brain — Habit & Goal Coach", layout="wide")
    st.title("🧠 The Brain That Helps You Use Your Brain")
    st.write("ML-powered habit coach, roadmap suggestions, and achievement badges. Built for learners and doers.")

    conn = init_db()
    skill_df = get_sample_skill_df()

    # Sidebar: user profile
    st.sidebar.header("Your Profile")
    user_id = st.sidebar.text_input("Username (unique)", value="syedmra102")
    display_name = st.sidebar.text_input("Display name", value="Imran")
    chosen_field = st.sidebar.text_input("Chosen field (will save as preference)", value="Cricket")
    if st.sidebar.button("Save profile"):
        create_or_update_user(conn, user_id, display_name, chosen_field)
        st.sidebar.success("Profile saved!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Daily Motivation")
    st.sidebar.write(random.choice(MOTIVATIONAL_QUOTES))
    st.sidebar.markdown("---")
    # Quick leaderboard
    if st.sidebar.checkbox("Show leaderboard"):
        c = conn.cursor()
        c.execute("SELECT display_name, total_hours, streak_days, badges FROM users ORDER BY total_hours DESC LIMIT 10")
        rows = c.fetchall()
        if rows:
            lb = pd.DataFrame(rows, columns=["Name","Total Hours","Streak Days","Badges"])
            st.sidebar.table(lb)
        else:
            st.sidebar.info("No users yet — be the first!")

    # Main columns
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Set Goal & Log Today's Progress")
        interests_input = st.text_input("List your interests (comma separated) — examples: coding, math, creativity")
        interests = [i.strip().lower() for i in interests_input.split(",") if i.strip()] if interests_input else []
        st.caption("Pick skills/areas like: math, coding, research, security, biology, creativity")

        field = st.text_input("Your current target field (e.g., Cricket, Data Science)", value=chosen_field)
        hours_today = st.number_input("Hours you worked today on this field", min_value=0.0, max_value=24.0, value=0.0, step=0.5)
        distraction_text = st.text_input("Describe distractions you faced today (or type 'None')", value="None")

        # Analyze & Save button
        if st.button("Analyze & Save Today"):
            # ensure profile exists
            create_or_update_user(conn, user_id, display_name, field)
            # Recommendation (if user provided interests)
            if interests:
                recommended = recommend_goal(interests, skill_df)
                st.success(f"Recommended field based on interests: **{recommended}**")
                if recommended != field:
                    st.info(f"Suggestion: consider exploring **{recommended}** (based on your interests).")
            # Predict progress
            months, years, new_total = predict_progress(hours_today, total_hours=get_user(conn, user_id)["total_hours"] if get_user(conn, user_id) else 0)
            if months is not None:
                st.metric("Estimated time to mastery", f"{months} months (~{years} years)")
            else:
                st.info("Log some hours per day to get a time estimate.")

            # Detect distraction
            is_distracted = detect_distractions(distraction_text)
            if is_distracted:
                st.warning("Distraction detected — consider reducing it and logging distraction-free days.")
            else:
                st.success("Great — no major distraction detected today!")

            # Enforce stage hours progression: user must satisfy current stage target
            user = get_user(conn, user_id)
            if user is None:
                create_or_update_user(conn, user_id, display_name, field)
                user = get_user(conn, user_id)
            current_stage = user["hour_stage"]
            required_hours = HOUR_STAGES.get(current_stage, 6)
            if hours_today < required_hours:
                st.info(f"Stage {current_stage} target is {required_hours} hrs/day. You logged {hours_today} — keep trying! (Aim to hit {required_hours} to progress.)")
            else:
                # If they reached required hours, they can progress stage next time (we'll increment stage only if they consistently meet, but for simplicity increment)
                if current_stage < 3 and hours_today >= required_hours:
                    # progress stage after meeting required hours for one day — you could require multiple days in production
                    new_stage = current_stage + 1
                    c = conn.cursor()
                    c.execute("UPDATE users SET hour_stage = ? WHERE user_id = ?", (new_stage, user_id))
                    conn.commit()
                    st.success(f"Congrats! You have advanced to Stage {new_stage} (target {HOUR_STAGES[new_stage]} hrs/day).")

            # Log today's entry
            today_iso = date.today().isoformat()
            distraction_free_flag = 0 if is_distracted else 1
            badges = log_daily_entry(conn, user_id, today_iso, distraction_free_flag, hours_today)
            if badges:
                st.balloons()
                st.success(f"New badges / current badges: {', '.join(badges)}")
            else:
                st.info("No new badges today — consistency is key.")

    with col2:
        st.header("Quick Insights & Roadmap")
        # show user info
        user = get_user(conn, user_id)
        if user:
            st.subheader(f"{user['display_name']} — {user['field']}")
            st.write(f"Stage: {user['hour_stage']} (target {HOUR_STAGES.get(user['hour_stage'],6)} hrs/day)")
            st.write(f"Total hours logged: {user['total_hours']:.1f}")
            st.write(f"Streak days (distraction-free): {user['streak_days']}")
            st.write(f"Badges: {user['badges'] or 'None yet'}")
        else:
            st.info("Save your profile to see live stats here.")

        # Roadmap suggestion
        st.markdown("---")
        st.subheader("Personalized Roadmap")
        if st.button("Get roadmap for my field"):
            connx = conn
            steps, month1, tips = get_roadmap(connx, field)
            st.write(f"**Starting Steps:** {steps}")
            st.write(f"**1-Month Plan:** {month1}")
            st.write(f"**Uniqueness Tips:** {tips}")

        st.markdown("---")
        st.subheader("Historic Progress")
        # show recent 30 days by default
        c = conn.cursor()
        c.execute("SELECT entry_date, distraction_free, hours_logged FROM daily_entries WHERE user_id = ? ORDER BY entry_date DESC LIMIT 60", (user_id,))
        rows = c.fetchall()
        if rows:
            df_hist = pd.DataFrame(rows, columns=["date","distraction_free","hours"])
            df_hist["date"] = pd.to_datetime(df_hist["date"])
            df_hist = df_hist.sort_values("date")
            st.line_chart(df_hist.set_index("date")[["hours","distraction_free"]])
            st.table(df_hist.tail(10).assign(distraction_free=lambda d: d["distraction_free"].map({1:"Yes",0:"No"})))
        else:
            st.info("Log some days to visualize progress here.")

    # Bottom: simulator & what-if
    st.markdown("---")
    st.header("What-If Simulator")
    sim_hours = st.slider("Simulate committing hours/day", min_value=1.0, max_value=12.0, value=3.0)
    sim_months, sim_years, _ = predict_progress(sim_hours, total_hours=get_user(conn, user_id)["total_hours"] if get_user(conn, user_id) else 0)
    if sim_months is not None:
        st.write(f"If you do {sim_hours} hrs/day → approx {sim_months} months (~{sim_years} years) to mastery.")
    else:
        st.info("Increase daily hours to see a mastery estimate.")

    st.markdown("---")
    st.write("Built with ❤️ — keep consistent, document your learning, and good luck!")

    conn.close()

if __name__ == "__main__":
    main()
