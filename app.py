# --- ADDITIONS INSIDE app.py (replaces previous version) ---

def check_stage_progress(hours, distraction_free, exercise, diet, early_morning, streak_days):
    """
    Returns (stage, passed, message) based on conditions you defined.
    """
    # Stage 1: Silver
    if hours >= 2 and distraction_free and streak_days >= 15:
        return "Silver", True, "✅ You earned Silver: 15 days, 2 hrs/day, no distraction!"
    
    # Stage 2: Platinum
    if hours >= 4 and distraction_free and exercise and diet and streak_days >= 30:
        return "Platinum", True, "🏆 Platinum unlocked: 4 hrs/day, no distraction, exercise + diet!"
    
    # Stage 3: Gold
    if hours >= 6 and distraction_free and exercise and early_morning and streak_days >= 60:
        return "🥇 Gold", True, "🔥 Gold stage achieved: 6 hrs early morning + no distraction + exercise for 60 days!"
    
    return None, False, "Keep going — build streaks and meet requirements."


# --- IN MAIN UI (col1 block, replace Analyze & Save Today section) ---
if st.button("Analyze & Save Today"):
    create_or_update_user(conn, user_id, display_name, field)

    # New inputs
    exercise = st.checkbox("Did you exercise 1 hr today?")
    diet = st.checkbox("Did you maintain a healthy diet today?")
    early_morning = st.checkbox("Did you work early morning (6+ hrs)?")

    # Recommendation if interests given
    if interests:
        recommended = recommend_goal(interests, skill_df)
        st.success(f"Recommended field: **{recommended}**")
        if recommended != field:
            st.info(f"Consider exploring {recommended} as well.")

    # Progress prediction
    months, years, new_total = predict_progress(hours_today, get_user(conn, user_id)["total_hours"] if get_user(conn, user_id) else 0)
    if months is not None:
        st.metric("Time to mastery", f"{months} months (~{years} years)")

    # Detect distractions + log
    is_distracted = detect_distractions(distraction_text)
    if is_distracted:
        st.warning(f"🚨 Distraction detected today: {distraction_text}")
    else:
        st.success("✅ No distraction logged today.")

    # Log entry
    today_iso = date.today().isoformat()
    distraction_free_flag = 0 if is_distracted else 1
    badges = log_daily_entry(conn, user_id, today_iso, distraction_free_flag, hours_today)

    # Stage progression
    stage, passed, msg = check_stage_progress(hours_today, not is_distracted, exercise, diet, early_morning, get_user(conn, user_id)["streak_days"])
    if passed:
        st.balloons()
        st.success(msg)
    else:
        st.info(msg)

    # Show badges
    if badges:
        st.write(f"🎖️ Current badges: {', '.join(badges)}")

# --- IN RIGHT COLUMN (col2), add Stage Progress overview ---
st.subheader("Stage Progress Tracker")
user = get_user(conn, user_id)
if user:
    streak = user["streak_days"]
    hrs = user["total_hours"]
    st.write(f"📊 Current streak: {streak} days | Total hrs: {hrs:.1f}")
    st.write("Silver → Platinum → Gold system:")
    st.markdown("- **Silver**: 15 days, 2 hrs/day, no distractions")
    st.markdown("- **Platinum**: 30 days, 4 hrs/day, no distractions, + exercise + diet")
    st.markdown("- **Gold**: 60 days, 6 hrs/day early morning, no distractions, + exercise")
else:
    st.info("Log progress to unlock stage tracking.")
