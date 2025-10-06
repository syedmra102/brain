import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('user_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT, field TEXT, hours_per_day REAL, distractions TEXT, 
                  streak_days INTEGER, badges TEXT, last_updated TEXT)''')
    conn.commit()
    return conn

def update_user(conn, user_id, field, hours_per_day, distractions, streak_days):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, field, hours_per_day, distractions, streak_days, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, field, hours_per_day, distractions, streak_days, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()