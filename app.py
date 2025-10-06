import streamlit as st
import sqlite3
from datetime import datetime

# ---------------------------
# Database Setup
# ---------------------------
def init_db():
    conn = sqlite3.connect("challenge.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS progress
                 (name TEXT, distraction TEXT, goal TEXT, current_stage INT, 
                 day_count INT, last_update TEXT, current_hours INT)''')
    conn.commit()
    conn.close()

def save_progress(name, distraction, goal, current_stage, day_count, current_hours):
    conn = sqlite3.connect("challenge.db")
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    # Check if user already exists
    c.execute("SELECT * FROM progress WHERE name=?", (name,))
    row = c.fetchone()

    if row:
        last_update = row[5]
        if last_update != today:  # only count once per day
            day_count += 1
        c.execute("""UPDATE progress SET distraction=?, goal=?, current_stage=?, 
                     day_count=?, last_update=?, current_hours=? WHERE name=?""",
                  (distraction, goal, current_stage, day_count, today, current_hours, name))
    else:
        c.execute("INSERT INTO progress VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (name, distraction, goal, current_stage, 1, today, current_hours))

    conn.commit()
    conn.close()

def load_progress(name):
    conn = sqlite3.connect("challenge.db")
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
# Hour Stages (2 → 4 → 6 hrs)
# ---------------------------
def get_hour_stage(stage):
    if stage == 1:
        return 2
    elif stage == 2:
        return 4
    else:
        return 6

# ---------------------------
# Streamlit App
# ---------------------------
def main():
    st.title("🧠 Brain – Habit & Distraction Challenge")

    init_db()

    name = st.text_input("Enter your name:")
    goal = st.text_input("What is your main goal? (e.g., Become a Data Scientist)")
    distraction = st.text_input("Which distraction do you want to quit? (e.g., TikTok, Gaming)")
    current_hours = st.number_input("How many hours did you spend today on your goal?", min_value=0, max_value=24)

    if st.button("Save Today’s Progress"):
        if name and goal and distraction:
            progress = load_progress(name)
            if progress:
                stage = progress[3]  # current stage
                required_hours = get_hour_stage(stage)

                if current_hours < required_hours:
                    st.warning(f"⚠️ You need to reach at least {required_hours} hours/day before moving forward.")
                else:
                    # Increase stage if requirement is met for long enough
                    if stage == 1 and current_hours >= 2:
                        stage = 2
                    elif stage == 2 and current_hours >= 4:
                        stage = 3

                    save_progress(name, distraction, goal, stage, progress[4], current_hours)
                    st.success("✅ Progress saved successfully!")
            else:
                # First-time entry
                save_progress(name, distraction, goal, 1, 1, current_hours)
                st.success("✅ Challenge started!")
        else:
            st.warning("⚠️ Please fill in all fields.")

    if name:
        progress = load_progress(name)
        if progress:
            st.subheader(f"📊 Progress for {progress[0]}")
            st.write(f"**Goal:** {progress[2]}")
            st.write(f"**Distraction to quit:** {progress[1]}")
            st.write(f"**Current Stage:** {progress[3]} ({get_hour_stage(progress[3])} hrs/day target)")
            st.write(f"**Days Completed:** {progress[4]}")
            st.write(f"**Last Update:** {progress[5]}")
            st.write(f"**Today’s Hours:** {progress[6]}")

            grade = get_grade(progress[4])
            st.success(f"🏆 Current Level: {grade}")

# ---------------------------
if __name__ == "__main__":
    main()
