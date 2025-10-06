import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import date, timedelta
import random
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression

DB_PATH = "brain_user_data.db"

# ---------------------------
# DB Init
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            field TEXT,
            interests TEXT,
            free_hours REAL,
            current_hours REAL,
            stage TEXT,
            streak_days INTEGER DEFAULT 0,
            total_hours REAL DEFAULT 0,
            distractions TEXT,
            badges TEXT DEFAULT '',
            last_check TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            user_id TEXT,
            log_date TEXT,
            distraction_free INTEGER,
            hours REAL,
            PRIMARY KEY(user_id, log_date)
        )
    """)

    conn.commit()
    return conn

# ---------------------------
# Stage Logic
# ---------------------------
def determine_stage(current_hours, free_hours, distractions):
    distraction_free = (distractions.lower() in ["none","no","n/a"])
    if current_hours >= 6 and distraction_free and free_hours >= 6:
        return "Gold"
    elif current_hours >= 4 and distraction_free and free_hours >= 4:
        return "Platinum"
    elif current_hours >= 2 and distraction_free:
        return "Silver"
    else:
        return "Starter"

def check_stage_progress(stage, streak_days):
    if stage == "Silver" and streak_days >= 15:
        return True, "🥉 Silver passed! 15 days of focus!"
    elif stage == "Platinum" and streak_days >= 30:
        return True, "🏆 Platinum achieved! 30 days strong!"
    elif stage == "Gold" and streak_days >= 60:
        return True, "🔥 Gold achieved! 60 days monster mode!"
    return False, "Keep going! You’re on the right path."

# ---------------------------
# DB Helpers
# ---------------------------
def get_user(conn, user_id):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row: return None
    keys = ["user_id","name","field","interests","free_hours","current_hours","stage","streak_days","total_hours","distractions","badges","last_check"]
    return dict(zip(keys,row))

def save_user(conn, user_id, name, field, interests, free_hours, current_hours, distractions):
    stage = determine_stage(current_hours, free_hours, distractions)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO users 
                 (user_id,name,field,interests,free_hours,current_hours,stage,streak_days,total_hours,distractions,badges,last_check)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                 (user_id,name,field,interests,free_hours,current_hours,stage,0,0,distractions,"",""))
    conn.commit()
    return stage

def log_day(conn, user_id, today_hours, distraction_text):
    distraction_free = distraction_text.lower() in ["none","no","n/a",""]
    today = date.today().isoformat()
    c = conn.cursor()
    # insert log
    c.execute("INSERT OR REPLACE INTO logs VALUES (?,?,?,?)", (user_id,today,int(distraction_free),today_hours))
    # update streak & hours
    user = get_user(conn,user_id)
    streak = user["streak_days"] + 1 if distraction_free else 0
    total = user["total_hours"] + today_hours
    c.execute("UPDATE users SET streak_days=?, total_hours=?, last_check=? WHERE user_id=?",
              (streak,total,today,user_id))
    conn.commit()
    return streak,distraction_free

# ---------------------------
# Streamlit UI
# ---------------------------
def main():
    st.set_page_config(page_title="The Brain App", page_icon="🧠", layout="wide")
    st.title("🧠 The Brain That Helps You Use Your Brain")

    conn = init_db()

    st.sidebar.header("Profile Setup")
    user_id = st.sidebar.text_input("User ID (unique)", "syedmra102")
    user = get_user(conn,user_id)

    if not user:
        st.info("👉 Please create your profile first.")
        name = st.text_input("Your Name")
        field = st.text_input("Your Goal Field", "Programming")
        interests = st.text_input("Your Interests (comma separated)", "coding, math")
        free_hours = st.number_input("How many free hours/day do you have?", 0,24,4)
        current_hours = st.number_input("How many hours/day do you currently work on your goal?", 0,24,2)
        distractions = st.text_input("Main Distractions you face?", "social media")

        if st.button("Save Profile"):
            stage = save_user(conn,user_id,name,field,interests,free_hours,current_hours,distractions)
            st.success(f"✅ Profile created! You are starting at **{stage} stage**")
    else:
        st.success(f"Welcome back, {user['name']}! Current stage: **{user['stage']}**")

        st.header("Daily Log")
        today_hours = st.slider("How many hours did you work today?", 0,12,2)
        distraction_text = st.text_input("What distracted you today?", "None")

        if st.button("Submit Today’s Log"):
            streak,free = log_day(conn,user_id,today_hours,distraction_text)
            passed,msg = check_stage_progress(user["stage"],streak)
            if passed:
                st.balloons()
                st.success(msg)
            else:
                if free:
                    st.info(msg)
                else:
                    st.warning("Great! You will become the monster one day 💪 — stay consistent!")

            st.write(f"**Current Streak:** {streak} days")
            st.write(f"**Total Hours Worked:** {get_user(conn,user_id)['total_hours']}")

if __name__ == "__main__":
    main()
