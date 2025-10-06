import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression
import sqlite3
from datetime import datetime
import re
from textblob import TextBlob
import random
import os

# Database setup (supports savings for pocket money)
def init_db():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, field TEXT, hours_per_day REAL, distractions TEXT, 
                  streak_days INTEGER, badges TEXT, last_updated TEXT, total_hours REAL, savings REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS roadmaps 
                 (field TEXT PRIMARY KEY, starting_steps TEXT, month1_plan TEXT, uniqueness_tips TEXT)''')
    sample_roadmaps = [
        ("Cricket", "Join a local club; focus on fitness.", "Practice batting/bowling 3x/week; watch tutorials.", "Develop agility for spin bowling if tall."),
        ("Programming", "Learn Python basics on Codecademy.", "Build 1 CLI app; contribute to GitHub.", "Specialize in ML for healthcare apps."),
        ("Music", "Practice scales daily; use free apps like Yousician.", "Compose 1 simple song; join online jam sessions.", "Blend genres like fusion for uniqueness.")
    ]
    for field, steps, month1, tips in sample_roadmaps:
        c.execute("INSERT OR REPLACE INTO roadmaps (field, starting_steps, month1_plan, uniqueness_tips) VALUES (?, ?, ?, ?)",
                  (field, steps, month1, tips))
    conn.commit()
    return conn

# Load synthetic data
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    return df

# ML: Goal recommendation
def recommend_goal(interests, df):
    interest_vector = np.zeros(len(df.columns[1:]))
    for interest in interests:
        if interest in df.columns[1:]:
            interest_vector[df.columns[1:].index(interest)] = 1
    similarities = cosine_similarity([interest_vector], df.iloc[:, 1:])[0]
    top_idx = np.argmax(similarities)
    return df['field'][top_idx]

# ML: Progress prediction
def predict_progress(hours_per_day, field, total_hours=0):
    X = np.array([[1], [2], [3], [4], [5], [6], [8]]).reshape(-1, 1)
    y = np.array([10000/1, 10000/2, 10000/3, 10000/4, 10000/5, 10000/6, 10000/8])
    model = LinearRegression().fit(X, y)
    days_remaining = model.predict(np.array([[hours_per_day]]))[0] - (total_hours / hours_per_day)
    months = max(0, round(days_remaining / 30, 1))
    years = round(months / 12, 1)
    return months, years, total_hours + (hours_per_day * 30)

# NLP: Distraction detection
def detect_distractions(distractions_avoided):
    return not distractions_avoided  # False means avoided, True means distracted

# Badge system
def update_badges(conn, user_id, hours_per_day, distractions_avoided, streak_days, total_hours):
    badges = []
    if distractions_avoided:
        if streak_days >= 15:
            badges.append('Silver (Distraction-Free - 15 days strong!)')
        if streak_days >= 45:
            badges.append('Platinum (Distraction-Free - 45 days unstoppable!)')
        if streak_days >= 105:
            badges.append('Gold (Distraction-Free - 105 days mastered!)')
    if hours_per_day >= 3 and streak_days >= 15:
        badges.append('Silver (Mastery - 3 hrs/day for 15 days)')
    if hours_per_day >= 6 and streak_days >= 30:
        badges.append('Platinum (Mastery - 6 hrs/day for 30 days)')
    if hours_per_day >= 8 and streak_days >= 60:
        badges.append('Gold (Mastery - 8 hrs/day for 60 days - Habit formed!)')
    c = conn.cursor()
    c.execute("UPDATE users SET badges = ? WHERE user_id = ?", (','.join(badges), user_id))
    conn.commit()
    return badges

# Get roadmap
def get_roadmap(conn, field):
    c = conn.cursor()
    c.execute("SELECT starting_steps, month1_plan, uniqueness_tips FROM roadmaps WHERE field = ?", (field,))
    result = c.fetchone()
    if result:
        return result
    return "Start with basics and build daily habits!", "Focus on 1 month goals.", "Find your unique strength to stand out."

# New: Daily check-in with tick marks
def daily_check_in(conn, user_id, stage, distractions_avoided, work_done, sleep_early, pushups=0, pocket_money=0):
    c = conn.cursor()
    c.execute("SELECT streak_days, savings FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    streak_days = result[0] if result else 0
    savings = result[1] if result else 0.0

    all_conditions_met = False
    if stage == "Silver":
        all_conditions_met = (distractions_avoided and work_done)
    elif stage == "Platinum":
        all_conditions_met = (distractions_avoided and work_done and pushups >= 30)
    elif stage == "Gold":
        all_conditions_met = (distractions_avoided and work_done and sleep_early and pushups >= 30)

    motivational_images = [
        ("images/motiv1.png", "Tum unstoppable ho! Keep pushing forward!"),
        ("images/motiv2.png", "Every small step counts! Stay focused!"),
        ("images/motiv3.png", "Your dreams are closer than you think!"),
        ("images/motiv4.png", "Discipline is your superpower!"),
    ]

    if all_conditions_met:
        streak_days += 1
        days_required = 15 if stage == "Silver" else 30 if stage == "Platinum" else 60
        days_left = days_required - streak_days
        image_path, quote = random.choice(motivational_images)
        message = f"Great start! Just {days_left} days more, start now! 🎉 Quote: {quote}"
    else:
        savings += pocket_money  # Add entire pocket money
        streak_days = 0  # Reset streak
        image_path, quote = motivational_images[0]  # Default image
        message = f"Conditions nahi poori hui! {pocket_money} PKR added to savings. Total: {savings} PKR. Try again tomorrow!"
    
    c.execute("UPDATE users SET streak_days = ?, savings = ? WHERE user_id = ?", (streak_days, savings, user_id))
    conn.commit()
    return message, streak_days, savings, image_path, quote

# Motivational quotes for sidebar
motivational_quotes = [
    "The journey of a thousand miles begins with one step. - Lao Tzu",
    "Success is the sum of small efforts repeated day in and day out. - Robert Collier",
    "You are never too old to set another goal or to dream a new dream. - C.S. Lewis"
]

# Streamlit UI
def main():
    st.set_page_config(page_title="The Brain App", page_icon="🧠", layout="wide")
    st.title("🧠 The Brain That Helps You to Use Your Brain!!")
    st.markdown("**Your personal ML coach for goals, habits, and mastery. For students and aimless people!**")

    # Sidebar
    st.sidebar.header("Your Profile")
    user_id = st.sidebar.text_input("User ID", value="syedmra102", key="user_id")
    if 'user_session' not in st.session_state:
        st.session_state.user_session = user_id

    # Main content
    col1, col2 = st.columns(2)
    with col1:
        st.header("Set Your Goals")
        interests = st.multiselect("Select Interests", ['Sports', 'Programming', 'Music', 'Art', 'Science', 'Business', 'Health'])
        field = st.text_input("Chosen Field (e.g., Cricket)", value="Cricket", key="field")
        hours_per_day = st.slider("Daily Hours", 0.0, 12.0, 3.0, key="hours")
        distractions = st.text_area("Describe Distractions (e.g., 'social media scrolling')", value="None", key="distractions")
        stage = st.selectbox("Current Stage", ["Silver", "Platinum", "Gold"], key="stage")

    with col2:
        st.header("ML Insights")
        if st.button("Analyze & Predict 🧠", key="submit"):
            conn = init_db()
            df = load_data()

            # ML: Recommend goal
            if interests:
                recommended_field = recommend_goal(interests, df)
                st.success(f"**Recommended Field:** {recommended_field}")
                if recommended_field != field:
                    st.info(f"Consider switching to {recommended_field} for better fit!")

            # ML: Predict progress
            months, years, updated_total_hours = predict_progress(hours_per_day, field)
            st.metric("Time to Mastery", f"{months} months / {years} years")
            st.info(f"Based on 10,000-hour rule: At {hours_per_day} hrs/day, you'll master {field}!")

            # Distraction detection
            if detect_distractions(distractions == "None"):
                st.warning("🚨 Distraction Detected! Reduce to build streaks.")
            else:
                st.success("✅ Focused! Keep it up to earn badges.")

            # Update database
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO users (user_id, field, hours_per_day, distractions, streak_days, total_hours, last_updated, savings) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (user_id, field, hours_per_day, distractions, 0, updated_total_hours, datetime.now().strftime('%Y-%m-%d'), 0.0))
            conn.commit()

            # Badges
            badges = update_badges(conn, user_id, hours_per_day, distractions == "None", 0, updated_total_hours)
            if badges:
                st.balloons()
                st.success(f"🎉 **Earned Badges:** {', '.join(badges)}")
            else:
                st.info("Keep consistent to unlock badges!")

            # Roadmap
            steps, month1, tips = get_roadmap(conn, field)
            st.subheader(f"Roadmap for {field}")
            st.write(f"**Starting Steps:** {steps}")
            st.write(f"**1-Month Plan:** {month1}")
            st.write(f"**Uniqueness Tips:** {tips}")

            conn.close()

    # New: Daily Check-In Form with Tick Marks
    st.header("Daily Check-In")
    with st.form(key="daily_check_in"):
        st.write("Fill this before sleeping! Just tick the boxes:")
        distractions_avoided = st.checkbox("I avoided distractions today", key="distractions_avoided")
        work_done = st.checkbox("I worked at least 2 hours on my field", key="work_done")
        sleep_early = st.checkbox("I slept early (before 10 PM, for Gold)", key="sleep_early")
        pushups = st.number_input("Pushups done today (for Platinum/Gold)", 0, 100, 0, key="pushups")
        pocket_money = st.number_input("Today's pocket money (PKR)", 0.0, 10000.0, 0.0, key="pocket_money")
        submit_check_in = st.form_submit_button("Submit Check-In")

        if submit_check_in:
            conn = init_db()
            message, streak_days, savings, image_path, quote = daily_check_in(conn, user_id, stage, distractions_avoided, work_done, sleep_early, pushups, pocket_money)
            st.write(message)
            if os.path.exists(image_path):
                st.image(image_path, caption="Screenshot this and set as your wallpaper to stay motivated!")
            else:
                st.warning("Image not found. Add motivational images to 'images/' folder in your repo.")
            st.metric("Current Streak", f"{streak_days} days")
            st.metric("Savings for Field", f"{savings} PKR")
            if stage == "Gold" and streak_days >= 60:
                st.success(f"🎉 Gold Badge Achieved! Use your {savings} PKR to develop your field (e.g., buy cricket gear or a course)!")
            conn.close()

    # Progress chart
    st.header("Your Progress Chart")
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT hours_per_day, total_hours, last_updated FROM users WHERE user_id = ?", (user_id,))
    data = c.fetchall()
    if data:
        df_progress = pd.DataFrame(data, columns=['Daily Hours', 'Total Hours', 'Date'])
        st.line_chart(df_progress.set_index('Date')[['Daily Hours', 'Total Hours']])
        st.metric("Total Hours Invested", df_progress['Total Hours'].iloc[-1])
    else:
        st.info("Log your first session to see charts!")
    conn.close()

    # Motivational quote
    st.sidebar.subheader("Daily Motivation")
    st.sidebar.write(random.choice(motivational_quotes))

    # What If Simulator
    st.header("What If Simulator")
    sim_hours = st.slider("Simulate different daily hours", 1.0, 10.0, 4.0)
    sim_months, sim_years, _ = predict_progress(sim_hours, field)
    st.write(f"If you commit {sim_hours} hrs/day: Mastery in {sim_months} months / {sim_years} years!")

if __name__ == "__main__":
    main()
