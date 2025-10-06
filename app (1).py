import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression
import sqlite3
from datetime import datetime, timedelta
import re

# Database setup (connect to SQLite)
def init_db():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT, field TEXT, hours_per_day REAL, distractions TEXT, 
                  streak_days INTEGER, badges TEXT, last_updated TEXT)''')
    conn.commit()
    return conn

# Load synthetic data for ML
@st.cache_data
def load_data():
    df = pd.read_csv('data.csv')
    return df

# Collaborative filtering for goal recommendation
def recommend_goal(interests, df):
    interest_vector = np.zeros(len(df.columns[1:]))
    for interest in interests:
        if interest in df.columns[1:]:
            interest_vector[df.columns[1:].index(interest)] = 1
    similarities = cosine_similarity([interest_vector], df.iloc[:, 1:])[0]
    top_idx = np.argmax(similarities)
    return df['field'][top_idx]

# Progress prediction (time to mastery)
def predict_progress(hours_per_day, field):
    # Synthetic model: 10,000 hours for mastery
    X = np.array([[1], [2], [3], [4], [5]]).reshape(-1, 1)  # Hours/day
    y = np.array([10000/1, 10000/2, 10000/3, 10000/4, 10000/5])  # Days to mastery
    model = LinearRegression().fit(X, y)
    days = model.predict(np.array([[hours_per_day]]))[0]
    return round(days / 30, 1)  # Months

# Distraction detection (basic NLP)
def detect_distractions(text):
    distraction_keywords = ['social media', 'gaming', 'scrolling', 'tv']
    for keyword in distraction_keywords:
        if re.search(keyword, text.lower()):
            return True
    return False

# Update badges
def update_badges(conn, user_id, hours_per_day, distractions, streak_days):
    badges = []
    if distractions == 'None' or not detect_distractions(distractions):
        if streak_days >= 15:
            badges.append('Silver (Distraction-Free)')
        if streak_days >= 45:
            badges.append('Platinum (Distraction-Free)')
        if streak_days >= 105:
            badges.append('Gold (Distraction-Free)')
    if hours_per_day >= 3 and streak_days >= 15:
        badges.append('Silver (Mastery)')
    if hours_per_day >= 6 and streak_days >= 30:
        badges.append('Platinum (Mastery)')
    if hours_per_day >= 8 and streak_days >= 60:
        badges.append('Gold (Mastery)')
    c = conn.cursor()
    c.execute("UPDATE users SET badges = ? WHERE user_id = ?", (','.join(badges), user_id))
    conn.commit()
    return badges

# Streamlit UI
def main():
    st.title("The Brain That Helps You to Use Your Brain!!")
    st.write("Set goals, track habits, and earn badges to master your field!")

    # User input
    user_id = st.text_input("Enter your ID (e.g., syedmra102)", "syedmra102")
    interests = st.multiselect("Select your interests", 
                              ['Sports', 'Programming', 'Music', 'Art', 'Science'])
    field = st.text_input("Enter your chosen field (e.g., Cricket)", "Cricket")
    hours_per_day = st.slider("Hours per day", 0.0, 10.0, 3.0)
    distractions = st.text_area("Describe distractions (e.g., social media)", "None")
    
    # Initialize database
    conn = init_db()
    
    # Submit button
    if st.button("Submit"):
        # ML: Recommend goal
        df = load_data()
        if not interests:
            st.warning("Please select at least one interest.")
        else:
            recommended_field = recommend_goal(interests, df)
            st.success(f"Recommended field: {recommended_field}")

        # ML: Predict progress
        months = predict_progress(hours_per_day, field)
        st.write(f"Estimated time to mastery in {field}: {months} months")

        # Distraction detection
        if detect_distractions(distractions):
            st.warning("Distraction detected! Try reducing non-productive time.")
        else:
            st.success("Great job staying focused!")

        # Update database
        streak_days = 1  # Simplified; assumes daily update
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (user_id, field, hours_per_day, distractions, streak_days, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, field, hours_per_day, distractions, streak_days, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()

        # Badges
        badges = update_badges(conn, user_id, hours_per_day, distractions, streak_days)
        if badges:
            st.balloons()
            st.write(f"Earned badges: {', '.join(badges)}")
        else:
            st.write("Keep going to earn badges!")

    # Display progress chart
    c = conn.cursor()
    c.execute("SELECT hours_per_day, last_updated FROM users WHERE user_id = ?", (user_id,))
    data = c.fetchall()
    if data:
        df_progress = pd.DataFrame(data, columns=['Hours', 'Date'])
        st.line_chart(df_progress.set_index('Date')['Hours'])
    
    conn.close()

if __name__ == "__main__":
    main()