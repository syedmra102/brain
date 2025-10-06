import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression
import sqlite3
from datetime import datetime, timedelta
import re
from textblob import TextBlob  # For NLP sentiment analysis on distractions
import random  # For motivational quotes

# Database setup (enhanced for badges and roadmaps)
def init_db():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    
    # Always create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, field TEXT, hours_per_day REAL, distractions TEXT, 
                  streak_days INTEGER, badges TEXT, last_updated TEXT, total_hours REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS roadmaps 
                 (field TEXT PRIMARY KEY, starting_steps TEXT, month1_plan TEXT, uniqueness_tips TEXT)''')
    
    # Pre-populate roadmaps if empty
    c.execute("SELECT COUNT(*) FROM roadmaps")
    if c.fetchone()[0] == 0:
        sample_roadmaps = [
            ("Cricket", "Join a local club; focus on fitness.", "Practice batting/bowling 3x/week; watch tutorials.", "Develop agility for spin bowling if tall."),
            ("Programming", "Learn Python basics on Codecademy.", "Build 1 CLI app; contribute to GitHub.", "Specialize in ML for healthcare apps."),
            ("Music", "Practice scales daily; use free apps like Yousician.", "Compose 1 simple song; join online jam sessions.", "Blend genres like fusion for uniqueness."),
            ("Data Science", "Take free Kaggle courses.", "Analyze a dataset; build a model.", "Focus on ethical AI for social impact."),
            ("Business", "Read 'Rich Dad Poor Dad'; start a side hustle.", "Create a business plan; network on LinkedIn.", "Innovate in local markets like e-commerce in Pakistan.")
        ]
        for field, steps, month1, tips in sample_roadmaps:
            c.execute("INSERT OR REPLACE INTO roadmaps (field, starting_steps, month1_plan, uniqueness_tips) VALUES (?, ?, ?, ?)",
                      (field, steps, month1, tips))

    conn.commit()
    return conn


# Load synthetic data for ML recommendations
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    return df

# Enhanced goal recommendation (collaborative filtering)
def recommend_goal(interests, df):
    interest_vector = np.zeros(len(df.columns[1:]))
    for interest in interests:
        if interest in df.columns[1:]:
            interest_vector[df.columns[1:].index(interest)] = 1
    similarities = cosine_similarity([interest_vector], df.iloc[:, 1:])[0]
    top_idx = np.argmax(similarities)
    return df['field'][top_idx]

# Enhanced progress prediction (10,000-hour rule with simulation)
def predict_progress(hours_per_day, field, total_hours=0):
    # Simulate 10,000 hours for mastery
    X = np.array([[1], [2], [3], [4], [5], [6], [8]]).reshape(-1, 1)  # Hours/day
    y = np.array([10000/1, 10000/2, 10000/3, 10000/4, 10000/5, 10000/6, 10000/8])  # Days to mastery
    model = LinearRegression().fit(X, y)
    days_remaining = model.predict(np.array([[hours_per_day]]))[0] - (total_hours / hours_per_day)
    months = max(0, round(days_remaining / 30, 1))  # Months
    years = round(months / 12, 1)
    return months, years, total_hours + (hours_per_day * 30)  # Update total hours for 30 days

# Enhanced distraction detection (NLP with sentiment analysis)
def detect_distractions(text):
    if text.lower() == 'none':
        return False
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity  # Negative sentiment indicates distraction
    keywords = ['social media', 'gaming', 'scrolling', 'tv', 'procrastinating']
    has_keywords = any(re.search(keyword, text.lower()) for keyword in keywords)
    return sentiment < 0 or has_keywords

# Enhanced badge system (your idea: distraction-free and mastery paths)
def update_badges(conn, user_id, hours_per_day, distractions, streak_days, total_hours):
    badges = []
    is_distracted = detect_distractions(distractions)
    if not is_distracted:
        if streak_days >= 15:
            badges.append('Silver (Distraction-Free - 15 days strong!)')
        if streak_days >= 45:
            badges.append('Platinum (Distraction-Free - 45 days unstoppable!)')
        if streak_days >= 105:
            badges.append('Gold (Distraction-Free - 105 days mastered!)')
    # Mastery badges (based on hours/day and streak)
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

# Get roadmap (rule-based, based on your idea)
def get_roadmap(conn, field):
    c = conn.cursor()
    c.execute("SELECT starting_steps, month1_plan, uniqueness_tips FROM roadmaps WHERE field = ?", (field,))
    result = c.fetchone()
    if result:
        return result
    return "Roadmap not found. Start with basics and build daily habits!", "Focus on 1 month goals.", "Find your unique strength to stand out."

# Motivational quotes (random for engagement)
motivational_quotes = [
    "The journey of a thousand miles begins with one step. - Lao Tzu",
    "Success is the sum of small efforts repeated day in and day out. - Robert Collier",
    "You are never too old to set another goal or to dream a new dream. - C.S. Lewis"
]

# Streamlit UI (top-notch: sidebar, charts, simulations)
def main():
    st.set_page_config(page_title="The Brain App", page_icon="🧠", layout="wide")
    st.title("🧠 The Brain That Helps You to Use Your Brain!!")
    st.markdown("**Your personal ML coach for goals, habits, and mastery. Based on your idea to help students and aimless people!**")

    # Sidebar for user profile
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
        streak_days = st.number_input("Current Streak Days", 0, 365, 1, key="streak")

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
            if detect_distractions(distractions):
                st.warning("🚨 Distraction Detected! (High sentiment or keywords like 'gaming'). Reduce to build streaks.")
            else:
                st.success("✅ Focused! Keep it up to earn badges.")

            # Update database
            c = conn.cursor()
            c.execute("SELECT hours_per_day, total_hours, last_updated FROM users WHERE user_id = ?", (user_id,))
            data = c.fetchall()

             if data:
                     df_progress = pd.DataFrame(data, columns=['Daily Hours', 'Total Hours', 'Date'])
                     st.line_chart(df_progress.set_index('Date')[['Daily Hours', 'Total Hours']])
                     st.metric("Total Hours Invested", df_progress['Total Hours'].iloc[-1])
              else:
                    st.info("No progress yet! Log your first session to see charts.")


            
            # Roadmap (your idea: starting, 1-month, uniqueness)
            steps, month1, tips = get_roadmap(conn, field)
            st.subheader(f"Roadmap for {field}")
            st.write(f"**Starting Steps:** {steps}")
            st.write(f"**1-Month Plan:** {month1}")
            st.write(f"**Uniqueness Tips:** {tips}")

            conn.close()

    # Progress chart (enhanced with total hours)
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

    # Simulation "What If?"
    st.header("What If Simulator")
    sim_hours = st.slider("Simulate different daily hours", 1.0, 10.0, 4.0)
    sim_months, sim_years, _ = predict_progress(sim_hours, field)
    st.write(f"If you commit {sim_hours} hrs/day: Mastery in {sim_months} months / {sim_years} years!")

if __name__ == "__main__":
    main()
