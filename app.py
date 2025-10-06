# app.py
# The Brain — Final top-notch habit/goal/roadmap app for Streamlit Cloud
# - Robust DB schema + migrations
# - 3-stage habit system (Silver/Platinum/Gold)
# - Daily logging, streaks, badges, charts, leaderboard, recommendations

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import date, datetime, timedelta
import random
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression

# -----------------------
# CONFIG
# -----------------------
DB_PATH = "brain_user_data.db"
MOTIVATIONAL_QUOTES = [
    "The journey of a thousand miles begins with one step. — Lao Tzu",
    "Small daily improvements are the key to staggering long-term results.",
    "You are never too old to set another goal or to dream a new dream. — C.S. Lewis",
    "Focus on progress, not perfection."
]

HOUR_STAGES = {1: 2, 2: 4, 3: 6}  # stage -> required hours/day

# thresholds in days for distraction badges
DISTRACTION_THRESHOLDS = {"silver": 15, "platinum": 30, "gold": 60}
# mastery thresholds: (hours/day required, streak_days)
MASTERY_THRESHOLDS = {
    "silver": (2, 15),
    "platinum": (4, 30),
    "gold": (6, 60)
}

DISTRACTION_KEYWORDS = [
    "social media", "facebook", "instagram", "tiktok", "youtube",
    "gaming", "netflix", "tv", "scrolling", "procrastinate", "procrastination",
    "twitter", "snapchat", "reddit"
]

# -----------------------
# DB Utilities
# -----------------------
def init_db():
    """Initialize DB and ensure schema has required columns (safe migrations)."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    # create users table if missing
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT,
            field TEXT,
            hour_stage INTEGER DEFAULT 1,
            total_hours REAL DEFAULT 0,
            streak_days INTEGER DEFAULT 0,
            badges TEXT DEFAULT '',
            last_check TEXT DEFAULT '',
            interests TEXT DEFAULT ''
        )
    """)

    # create daily logs table
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            user_id TEXT,
            log_date TEXT,
            distraction_free INTEGER,
            hours REAL,
            exercise INTEGER,
            diet INTEGER,
            early_morning INTEGER,
            PRIMARY KEY(user_id, log_date)
        )
    """)

    # create roadmaps table
    c.execute("""
        CREATE TABLE IF NOT EXISTS roadmaps (
            field TEXT PRIMARY KEY,
            starting_steps TEXT,
            month1_plan TEXT,
            uniqueness_tips TEXT
        )
    """)

    # safe migration helpers: add missing columns if older DB lacks them
    # (SQLite raises OperationalError if column exists; we catch and ignore)
    try:
        c.execute("ALTER TABLE users ADD COLUMN interests TEXT DEFAULT ''")
    except Exception:
        pass

    conn.commit()
    return conn

# -----------------------
# Sample Skills DataFrame (for recommendations)
# -----------------------
def get_skill_df():
    data = {
        "field": ["Data Science", "Machine Learning", "Cybersecurity", "Cloud Computing",
                  "Network Engineering", "Cricket", "Programming", "Music", "Business", "Graphic Design"],
        "math":       [1,1,0,1,1,0,1,0,0,0],
        "coding":     [1,1,0,1,1,0,1,0,1,1],
        "research":   [1,1,0,0,0,0,1,0,1,0],
        "security":   [0,0,1,0,1,0,0,0,0,0],
        "biology":    [0,0,0,0,0,1,0,1,0,0],
        "creativity": [0,0,0,0,0,0,0,1,1,1]
    }
    return pd.DataFrame(data)

# -----------------------
# Business Logic
# -----------------------
def recommend_goal(interests, df):
    cols = list(df.columns[1:])
    interest_vector = np.zeros(len(cols))
    for interest in interests:
        interest = interest.strip().lower()
        if interest in cols:
            interest_vector[cols.index(interest)] = 1
    if interest_vector.sum() == 0:
        # fallback to random field
        return random.choice(df['field'].tolist())
    sims = cosine_similarity([interest_vector], df.iloc[:, 1:])[0]
    top_idx = int(np.argmax(sims))
    return df['field'].iloc[top_idx]

def predict_progress(hours_per_day, total_hours=0):
    # Based on 10k-hour idea — regression to estimate days
    X = np.array([[1],[2],[3],[4],[5],[6],[8]]).reshape(-1,1)
    y = np.array([10000/1,10000/2,10000/3,10000/4,10000/5,10000/6,10000/8])
    model = LinearRegression().fit(X,y)
    if hours_per_day <= 0:
        return None, None, total_hours
    days_to_master = float(model.predict([[hours_per_day]])[0])
    days_remaining = max(0.0, days_to_master - (total_hours / max(1.0, hours_per_day)))
    months = round(days_remaining / 30.0, 1)
    years = round(months / 12.0, 2)
    new_total = total_hours + (hours_per_day * 30)
    return months, years, new_total

def detect_distractions(text):
    if not text:
        return False
    t = text.strip().lower()
    if t in ("none", "no", "n/a", "na", "nothing"):
        return False
    # keyword check
    for kw in DISTRACTION_KEYWORDS:
        if kw in t:
            return True
    # simple heuristic: presence of negative words
    negatives = ["addicted", "can't stop", "cant stop", "cannot stop", "wasting", "waste time", "can't focus", "cant focus"]
    for n in negatives:
        if n in t:
            return True
    return False

def compute_streak(conn, user_id):
    """Compute consecutive distraction-free days up to today."""
    c = conn.cursor()
    today = date.today()
    streak = 0
    for i in range(0, 365):  # upper limit
        d = (today - timedelta(days=i)).isoformat()
        c.execute("SELECT distraction_free FROM logs WHERE user_id=? AND log_date=?", (user_id, d))
        r = c.fetchone()
        if r and r[0] == 1:
            streak += 1
        else:
            break
    return streak

def update_badges(conn, user_id):
    """Compute and store badges for a user based on streak and total hours."""
    c = conn.cursor()
    c.execute("SELECT streak_days, total_hours, hour_stage, badges FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        return []
    streak_days, total_hours, hour_stage, existing_badges = row
    existing = set(b for b in existing_badges.split(",") if b)
    new_badges = set()

    # Distraction badges
    if streak_days >= DISTRACTION_THRESHOLDS["gold"]:
        new_badges.add("Gold (Distraction-Free)")
    elif streak_days >= DISTRACTION_THRESHOLDS["platinum"]:
        new_badges.add("Platinum (Distraction-Free)")
    elif streak_days >= DISTRACTION_THRESHOLDS["silver"]:
        new_badges.add("Silver (Distraction-Free)")

    # Mastery badges (simple: total_hours threshold)
    if total_hours >= (MASTERY_THRESHOLDS["gold"][0] * MASTERY_THRESHOLDS["gold"][1]):
        new_badges.add("Gold (Mastery)")
    elif total_hours >= (MASTERY_THRESHOLDS["platinum"][0] * MASTERY_THRESHOLDS["platinum"][1]):
        new_badges.add("Platinum (Mastery)")
    elif total_hours >= (MASTERY_THRESHOLDS["silver"][0] * MASTERY_THRESHOLDS["silver"][1]):
        new_badges.add("Silver (Mastery)")

    all_badges = sorted(list(existing.union(new_badges)))
    c.execute("UPDATE users SET badges=? WHERE user_id=?", (",".join(all_badges), user_id))
    conn.commit()
    return list(all_badges)

# -----------------------
# DB operations: get/create/update user and logs
# -----------------------
def get_user(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT user_id, display_name, field, hour_stage, total_hours, streak_days, badges, last_check, interests FROM users WHERE user_id=?", (user_id,))
    r = c.fetchone()
    if not r:
        return None
    keys = ["user_id","display_name","field","hour_stage","total_hours","streak_days","badges","last_check","interests"]
    return dict(zip(keys, r))

def create_or_update_user(conn, user_id, display_name, field, interests_text=""):
    c = conn.cursor()
    now = date.today().isoformat()
    user = get_user(conn, user_id)
    if user:
        c.execute("UPDATE users SET display_name=?, field=?, interests=? WHERE user_id=?", (display_name, field, interests_text, user_id))
    else:
        c.execute("INSERT INTO users (user_id, display_name, field, hour_stage, total_hours, streak_days, badges, last_check, interests) VALUES (?, ?, ?, 1, 0, 0, '', ?, ?)",
                  (user_id, display_name, field, now, interests_text))
    conn.commit()

def log_daily_entry(conn, user_id, distraction_free, hours, exercise, diet, early_morning):
    c = conn.cursor()
    today = date.today().isoformat()
    # Upsert log
    c.execute("""
        INSERT OR REPLACE INTO logs (user_id, log_date, distraction_free, hours, exercise, diet, early_morning)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, today, int(distraction_free), float(hours), int(bool(exercise)), int(bool(diet)), int(bool(early_morning))))
    conn.commit()

    # Recalculate total hours and streak
    c.execute("SELECT COALESCE(SUM(hours),0) FROM logs WHERE user_id=?", (user_id,))
    total = c.fetchone()[0] or 0.0
    streak = compute_streak(conn, user_id)

    # preserve existing display_name and field while updating totals
    user = get_user(conn, user_id)
    display_name = user["display_name"] if user else "Anonymous"
    field = user["field"] if user else "Unknown"

    c.execute("""
        INSERT OR REPLACE INTO users (user_id, display_name, field, hour_stage, total_hours, streak_days, badges, last_check, interests)
        VALUES (?, ?, ?, COALESCE((SELECT hour_stage FROM users WHERE user_id=?),1), ?, ?, COALESCE((SELECT badges FROM users WHERE user_id=?),''), ?, COALESCE((SELECT interests FROM users WHERE user_id?), ''))
    """, (user_id, display_name, field, user_id, total, streak, user_id, today, user_id))
    conn.commit()

    # Update badges after log
    badges = update_badges(conn, user_id)
    return badges

def get_logs(conn, user_id, days=60):
    c = conn.cursor()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    c.execute("SELECT log_date, distraction_free, hours, exercise, diet, early_morning FROM logs WHERE user_id=? AND log_date>=? ORDER BY log_date ASC", (user_id, cutoff))
    rows = c.fetchall()
    df = pd.DataFrame(rows, columns=["date","distraction_free","hours","exercise","diet","early_morning"])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

# -----------------------
# Stage checking with exact conditions
# -----------------------
def check_stage_conditions(hours_today, distraction_free, exercise, diet, early_morning, streak_days):
    """
    Returns (earned_stage_str or None, message)
    Conditions:
    - Silver: 2 hrs/day & distraction_free & 15-day streak
    - Platinum: 4 hrs/day & distraction_free & exercise & diet & 30-day streak
    - Gold: 6 hrs/day early_morning & distraction_free & exercise & 60-day streak
    """
    if hours_today >= 6 and distraction_free and exercise and early_morning and streak_days >= 60:
        return "Gold", "🔥 Gold achieved: 60 days, 6 hrs early morning + exercise + distraction-free"
    if hours_today >= 4 and distraction_free and exercise and diet and streak_days >= 30:
        return "Platinum", "🏆 Platinum achieved: 30 days, 4 hrs/day + exercise + diet + distraction-free"
    if hours_today >= 2 and distraction_free and streak_days >= 15:
        return "Silver", "🥉 Silver achieved: 15 days, 2 hrs/day + distraction-free"
    return None, "Keep going — follow the daily plan to reach the next stage."

# -----------------------
# UI: Main App
# -----------------------
def main():
    st.set_page_config(page_title="🧠 The Brain — Habit & Goal Coach", page_icon="🧠", layout="wide")
    st.title("🧠 The Brain That Helps You Use Your Brain")
    st.markdown("**Personal ML-backed coach for goals, streaks, and mastery.**")
    conn = init_db()
    skill_df = get_skill_df()

    # Sidebar: profile
    st.sidebar.header("Profile")
    user_id = st.sidebar.text_input("Unique Username", value="syedmra102")
    display_name = st.sidebar.text_input("Your name", value="Imran")
    chosen_field = st.sidebar.text_input("Preferred field", value="Cricket")
    interests_text = st.sidebar.text_input("Interests (comma-separated)", value="coding, math")
    if st.sidebar.button("Save Profile"):
        create_or_update_user(conn, user_id, display_name, chosen_field, interests_text)
        st.sidebar.success("Profile saved!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Daily Motivation")
    st.sidebar.write(random.choice(MOTIVATIONAL_QUOTES))
    st.sidebar.markdown("---")
    if st.sidebar.checkbox("Show Leaderboard"):
        c = conn.cursor()
        c.execute("SELECT display_name, total_hours, streak_days, badges FROM users ORDER BY total_hours DESC LIMIT 10")
        rows = c.fetchall()
        if rows:
            lb = pd.DataFrame(rows, columns=["Name","Total Hours","Streak Days","Badges"])
            st.sidebar.table(lb)
        else:
            st.sidebar.info("No users yet — be the first!")

    # Main layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Log Today's Session")
        st.write("Fill today's activity. This app rewards distraction-free consistency and staged mastery.")
        field = st.text_input("Target Field (what are you working on?)", value=chosen_field)
        hours_today = st.slider("Hours you worked today", 0.0, 12.0, 0.0, 0.5)
        distraction_text = st.text_input("Describe distractions today (or type 'None')", value="None")
        exercise = st.checkbox("Did you exercise 1 hour today?")
        diet = st.checkbox("Did you maintain a healthy diet today?")
        early_morning = st.checkbox("Did you work early morning today (e.g., before 8 AM)?")

        if st.button("Analyze & Save Today"):
            # ensure profile exists and saved
            create_or_update_user(conn, user_id, display_name, field, interests_text)
            # detect distraction
            distracted = detect_distractions(distraction_text)
            distraction_free = not distracted

            # recommendation if interests provided
            interests = [i.strip().lower() for i in interests_text.split(",") if i.strip()]
            if interests:
                rec = recommend_goal(interests, skill_df)
                st.success(f"Recommended field based on interests: **{rec}**")
                if rec.lower() != field.lower():
                    st.info(f"Consider exploring **{rec}** as it matches your interests.")

            # predict progress (estimate)
            user = get_user(conn, user_id)
            total_hours = user["total_hours"] if user else 0.0
            months, years, new_total = predict_progress(hours_today, total_hours)
            if months is not None:
                st.metric("Estimated time to mastery", f"{months} months (~{years} years)")
            else:
                st.info("Log positive hours per day to get a mastery estimate.")

            # log today's entry
            badges = log_daily_entry(conn, user_id, distraction_free, hours_today, exercise, diet, early_morning)

            # compute new user state
            user = get_user(conn, user_id)

            # check stage conditions
            stage_earned, msg = check_stage_conditions(hours_today, distraction_free, exercise, diet, early_morning, user["streak_days"])
            if stage_earned:
                # append stage badge if not already present
                current_badges = set(b for b in (user["badges"] or "").split(",") if b)
                stage_badge = f"{stage_earned} Stage"
                if stage_badge not in current_badges:
                    current_badges.add(stage_badge)
                    c = conn.cursor()
                    c.execute("UPDATE users SET badges=? WHERE user_id=?", (",".join(sorted(current_badges)), user_id))
                    conn.commit()
                    st.balloons()
                    st.success(f"{msg} — Badge awarded: {stage_badge}")
                else:
                    st.info(f"{msg} — you already have the {stage_badge} badge.")
            else:
                st.info(msg)

            # show current badges
            user = get_user(conn, user_id)
            st.write("**Current Badges:**", user["badges"] or "No badges yet — keep consistent!")

    with col2:
        st.header("Your Dashboard")
        user = get_user(conn, user_id)
        if user:
            st.subheader(f"{user['display_name']} — {user['field']}")
            st.write(f"**Interests:** {user['interests'] or interests_text or '—'}")
            st.write(f"**Current Stage Target:** Stage {user['hour_stage']} → {HOUR_STAGES.get(user['hour_stage'],6)} hrs/day")
            st.write(f"**Streak (distraction-free days):** {user['streak_days']}")
            st.write(f"**Total Hours Logged:** {user['total_hours']:.1f}")
            st.write(f"**Badges:** {user['badges'] or 'None yet'}")

            # logs / historic view
            df_logs = get_logs(conn, user_id, days=120)
            if not df_logs.empty:
                st.markdown("**History (last 120 days)**")
                # show a line chart for hours
                chart_df = df_logs.set_index("date").resample("D").sum()["hours"]
                st.line_chart(chart_df.fillna(0))

                # table with newest entries on top
                st.dataframe(df_logs.sort_values("date", ascending=False).head(30).assign(
                    distraction_free=lambda d: d["distraction_free"].map({1:"Yes",0:"No"}),
                    exercise=lambda d: d["exercise"].map({1:"Yes",0:"No"}),
                    diet=lambda d: d["diet"].map({1:"Yes",0:"No"}),
                    early_morning=lambda d: d["early_morning"].map({1:"Yes",0:"No"})
                )[["date","hours","distraction_free","exercise","diet","early_morning"]])
            else:
                st.info("No logs found. Log your first day to populate the dashboard!")

            # stage progress display (how close to next stage)
            st.markdown("---")
            st.subheader("Stage Progress Summary")
            # compute approximate progress for next stage
            current_streak = user["streak_days"]
            current_total = user["total_hours"]
            # show target badges status
            st.write("- Silver: 15 days streak & 2 hrs/day")
            st.write("- Platinum: 30 days streak & 4 hrs/day + exercise + diet")
            st.write("- Gold: 60 days streak & 6 hrs early morning + exercise")
            st.markdown("**Quick status:**")
            st.write(f"Streak: {current_streak} / 60 (Gold target)")
            st.write(f"Total hours: {current_total:.1f}")

        else:
            st.info("Create and save your profile (sidebar) and log your first day.")

    # bottom: what-if simulator
    st.markdown("---")
    st.header("What-If Simulator")
    sim_hours = st.slider("Simulate committing hours/day", 1.0, 12.0, 3.0)
    user = get_user(conn, user_id)
    total_now = user["total_hours"] if user else 0.0
    months, years, _ = predict_progress(sim_hours, total_now)
    if months is not None:
        st.write(f"If you commit {sim_hours} hrs/day → approx **{months} months (~{years} years)** to mastery (10k hours heuristic).")
    else:
        st.info("Increase daily hours to get an estimate.")

    conn.close()

if __name__ == "__main__":
    main()
