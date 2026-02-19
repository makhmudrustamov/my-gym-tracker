import os
import streamlit as st
import db
import uuid
import datetime

db.create_table()

def set_background(image_path):
    if os.path.exists(image_path):
        import base64
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(f'<style>.stApp {{background-image: linear-gradient(rgba(0,0,0,0.85), rgba(0,0,0,0.85)), url("data:image/jpg;base64,{encoded}"); background-size: cover; background-attachment: fixed;}}</style>', unsafe_allow_html=True)

# --- AUTHENTICATION ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = None



    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.title("GYM TRACKER")
    tab1, tab2 = st.tabs(["LOG IN", "JOIN NOW"])
    
    with tab1:
        u = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        p = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        if st.button("SIGN IN"):
            res = db.login_user(u, p)
            if res:
                st.session_state.user_id, st.session_state.is_admin = res
                st.rerun()
            else: st.error("Invalid Credentials")
                
    with tab2:
        nu = st.text_input("New Username", key="reg_u", placeholder="New Username", label_visibility="collapsed")
        np = st.text_input("New Password", type="password", key="reg_p", placeholder="New Password", label_visibility="collapsed")
        if st.button("CREATE ACCOUNT"):
            success, message = db.create_user(nu, np)
            if success: st.success(message)
            else: st.warning(message)
    st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN APP ---
else:
    set_background("background.jpg")
    
    # Calendar Selection in Sidebar
    selected_date = st.sidebar.date_input("📅 Choose Date", datetime.date.today())
    day_name = selected_date.strftime("%A")
    
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.rerun()

    st.title(f"Workout: {selected_date.strftime('%b %d, %Y')}")

    # ADD SECTION (Only show for today or future to keep UI clean)
    if selected_date >= datetime.date.today():
        with st.expander("➕ Add New Exercise"):
            ex_name = st.text_input("Exercise Name")
            upload_method = st.radio("Media Source", ["Camera", "Gallery", "Video"], horizontal=True)
            uploaded_file = None
            m_type = "image"

            if upload_method == "Camera": uploaded_file = st.camera_input("Snap")
            elif upload_method == "Gallery": uploaded_file = st.file_uploader("Upload", type=['png', 'jpg', 'jpeg', 'gif'])
            else: 
                uploaded_file = st.file_uploader("Video", type=['mp4'])
                m_type = "video"

            if st.button("Add to Routine"):
                if ex_name and uploaded_file:
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    ext = uploaded_file.name.split('.')[-1] if hasattr(uploaded_file, 'name') else "jpg"
                    save_path = f"uploads/{uuid.uuid4().hex}.{ext}"
                    with open(save_path, "wb") as f: f.write(uploaded_file.getbuffer())
                    db.add_workout(st.session_state.user_id, day_name, ex_name, save_path, m_type, selected_date)
                    st.rerun()

    st.divider()

    # DISPLAY WORKOUTS - Optimized for Mobile
    workouts = db.get_workouts(st.session_state.user_id, selected_date)
    
    if not workouts:
        st.info("No exercises found for this date. Time to hit the gym! 💪")
    
    for wid, wname, wpath, wtype in workouts:
        # Using a clean title for the expander
        with st.expander(f"⚙️ {wname.upper()}", expanded=True):
            
            # On mobile, columns will automatically stack if they get too narrow
            col_media, col_data = st.columns([1, 1])
            
            with col_media:
                if wpath and os.path.exists(wpath):
                    if wtype == "video":
                        st.video(wpath)
                    else:
                        st.image(wpath, use_container_width=True)
            
            with col_data:
                # MODERN LOGGING FORM
                with st.form(f"set_form_{wid}"):
                    # On mobile, we stack these vertically for better tap precision
                    sn = st.number_input("Set Number", min_value=1, step=1, key=f"s{wid}")
                    sr = st.number_input("Reps", min_value=1, step=1, key=f"r{wid}")
                    sw = st.number_input("Weight (kg)", min_value=0.0, step=2.5, format="%.1f", key=f"w{wid}")
                    
                    if st.form_submit_button("💾 SAVE SET", use_container_width=True):
                        db.add_set(wid, sn, sw, sr)
                        st.rerun()
                
                # CLEAN HISTORY LIST
                sets = db.get_sets(wid)
                if sets:
                    st.markdown("---")
                    for s_num, s_w, s_r in sets:
                        st.write(f"✅ **Set {s_num}:** {s_w}kg × {s_r}")
            
            # Full-width delete button at the bottom
            if st.button(f"🗑️ Delete ", key=f"del{wid}", use_container_width=True):
                db.delete_workout(wid)
                st.rerun()
