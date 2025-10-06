import streamlit as st
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LinearRegression
import sqlite3
from datetime import datetime, timedelta
import re

# ---------------------------
# Utility Functions
# ---------------------------
def recommend_goal(interests, df):
    cols = list(df.columns[1:])  # skip the first column (e.g., field name)
    interest_vector = np.zeros(len(cols))

    for interest in interests:
        if interest in cols:
            interest_vector[cols.index(interest)] = 1

    similarity = cosine_similarity([interest_vector], df.iloc[:, 1:])
    recommended_index = np.argmax(similarity)
    return df.iloc[recommended_index, 0]  # first column = field name

def save_feedback(user, feedback, db="feedback.db"):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (user TEXT, feedback TEXT, date TEXT)''')
    c.execute("INSERT INTO feedback VALUES (?, ?, ?)",
              (user, feedback, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def load_feedback(db="feedback.db"):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute("SELECT * FROM feedback")
    rows = c.fetchall()
    conn.close()
    return rows

# ---------------------------
# Main App
# ---------------------------
def main():
    st.title("🧠 Brain – Career & Goal Recommendation App")
    st.write("This app helps you explore possible career paths based on your interests.")

    # Upload dataset
    uploaded_file = st.file_uploader("Upload your dataset (CSV)", type="csv")
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        st.subheader("Available Fields in Dataset")
        st.write(df.head())

        # User input
        user_name = st.text_input("Enter your name:")
        user_interests = st.text_area("Enter your interests (comma separated):")

        if st.button("Submit"):
            if user_name and user_interests:
                interests = [i.strip() for i in user_interests.split(",")]

                try:
                    recommended_field = recommend_goal(interests, df)
                    st.success(f"🎯 Recommended Field: **{recommended_field}**")
                except Exception as e:
                    st.error(f"Error in recommendation: {e}")

            else:
                st.warning("⚠️ Please enter your name and interests.")

    # Feedback section
    st.subheader("💬 Feedback")
    feedback_text = st.text_area("Leave your feedback here:")
    if st.button("Submit Feedback"):
        if feedback_text:
            save_feedback("Anonymous", feedback_text)
            st.success("✅ Feedback submitted successfully!")
        else:
            st.warning("Please enter feedback before submitting.")

    # Show feedback
    if st.checkbox("Show all feedback"):
        feedbacks = load_feedback()
        for f in feedbacks:
            st.write(f"📝 {f[0]} said: {f[1]} ({f[2]})")

# ---------------------------
if __name__ == "__main__":
    main()
