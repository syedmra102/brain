import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ---------------------------
# Database Setup
# ---------------------------
def init_db():
    conn = sqlite3.connect("progress.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (name TEXT, goal TEXT, interests TEXT, distractions TEXT, 
                 current_hours INT, available_hours INT, day_count INT, last_update TEXT)''')
    conn.commit()
    conn.close()

def save_progress(name, goal, interests, distractions, current_hours, available_hours):
    conn = sqlite3.connect("progress.db")
    c = conn.cursor()

    # Check if user already exists
    c.execute("SELECT * FROM progress WHERE name=?", (name,))
    row = c.fetchone()

    today = datetime.now().strftime("%Y-%m-%d")

    if row:
        # Update existing user progress (if last update is a new day)
        last_update = row[7]
        day_count = row[6]
        if last_update != today:
            day_count += 1
        c.execute("""UPDATE progress SET goal=?, interests=?, distractions=?, 
                     current_hours=?, available_hours=?, day_count=?, last_update=? 
                     WHERE name=?""",
                  (goal, interests, distractions, current_hours, available_hours, day_count, today, name))
    else:
        # Insert new user
        c.execute("INSERT INTO progress VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (name, goal, interests, distractions, current_hours, available_hours, 1, today))

    conn.commit()
    conn.close()

def load_progress(name):
    conn = sqlite3.connect("progress.db")
    c = conn.cursor()
    c.execute("SELECT * FROM progress WHERE name=?", (name,))
    row = c.fetchone()
    conn.close()
    return row

# ---------------------------
# Grading System
# ---------------------------
def get_grade(day_count):
    if day_count >= 60:
        return "🥇 Gold"
    elif day_count >= 30:
        return "🥈 Platinum"
    elif day_count >= 15:
        return "🥉 Silver"
    else:
        return "⏳ Keep Going!"

# ---------------------------
# Streamlit App
# ---------------------------
def main():
    st.title("🧠 Brain – Goal & Habit Tracker")
    st.write("Track your goals, distractions, hours, and build habits with a grading system.")

    init_db()

    name = st.text_input("Enter your name:")
    goal = st.text_input("What is your goal? (e.g., Become a Data Scientist, Cricketer, etc.)")
    interests = st.text_area("Enter your interests (comma separated):")
    distractions = st.text_area("What distractions do you want to reduce?")
    current_hours = st.number_input("How many hours do you currently spend daily on your goal?", min_value=0, max_value=24)
    available_hours = st.number_input("How many free hours do you have daily?", min_value=0, max_value=24)

    if st.button("Save Progress"):
        if name and goal:
            save_progress(name, goal, interests, distractions, current_hours, available_hours)
            st.success("✅ Progress saved successfully!")
        else:
            st.warning("⚠️ Please enter at least your name and goal.")

    if name:
        progress = load_progress(name)
        if progress:
            st.subheader(f"📊 Progress for {progress[0]}")
            st.write(f"**Goal:** {progress[1]}")
            st.write(f"**Interests:** {progress[2]}")
            st.write(f"**Distractions:** {progress[3]}")
            st.write(f"**Current Hours/Day:** {progress[4]}")
            st.write(f"**Available Hours/Day:** {progress[5]}")
            st.write(f"**Days Tracked:** {progress[6]}")
            st.write(f"**Last Update:** {progress[7]}")

            grade = get_grade(progress[6])
            st.success(f"🏆 Current Level: {grade}")

# ---------------------------
if __name__ == "__main__":
    main()
