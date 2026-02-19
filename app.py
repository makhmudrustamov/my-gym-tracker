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

def render_community_feed():
    st.title("Gym Community 🤝")
    
    with st.expander("📣 Share a PR or Update"):
        post_text = st.text_area("What's on your mind?", placeholder="e.g. Just hit a 100kg Bench! 🚀")
        post_media = st.file_uploader("Add a Photo/Video", type=['png', 'jpg', 'mp4'], key="community_upload")
        
        if st.button("Post to Feed"):
            if post_text or post_media:
                media_path = None
                if post_media:
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    media_path = f"uploads/post_{uuid.uuid4().hex}.{post_media.name.split('.')[-1]}"
                    with open(media_path, "wb") as f: f.write(post_media.getbuffer())
                
                db.add_post(st.session_state.user_id, st.session_state.username, post_text, media_path)
                st.success("Posted!")
                st.rerun()

    posts = db.get_posts()
    for pid, uid, username, content, m_path, tstamp in posts:
        with st.container(border=True):
            st.markdown(f"### 👤 {username}")
            st.caption(f"Posted on {tstamp[:16]}")
            st.write(content)
            
            if m_path:
                if m_path.endswith('.mp4'): st.video(m_path)
                else: st.image(m_path, use_container_width=True)
            
            comments = db.get_comments(pid)
            for c_user, c_text in comments:
                st.markdown(f"💬 **{c_user}**: {c_text}")
            
            with st.form(key=f"comm_{pid}", clear_on_submit=True):
                c_input = st.text_input("Add a comment...", key=f"in_{pid}")
                if st.form_submit_button("Reply"):
                    if c_input:
                        db.add_comment(pid, st.session_state.username, c_input)
                        st.rerun()

# --- AUTHENTICATION ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

if st.session_state.user_id is None:
    set_background("background.jpg")
    st.markdown("""
        <style>
        .login-card { background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(15px); border-radius: 20px; padding: 40px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8); width: 100%; max-width: 450px; margin: auto; text-align: center; }
        .stButton > button { width: 100%; border-radius: 10px; background-color: #ff4b4b; color: white; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.title("GYM TRACKER")
    tab1, tab2 = st.tabs(["LOG IN", "JOIN NOW"])
    
    with tab1:
        u = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        p = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        if st.button("SIGN IN"):
            res = db.login_user(u, p)
            if res:
                st.session_state.user_id, st.session_state.username, st.session_state.is_admin = res
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
    menu = st.sidebar.radio("Navigation", ["💪 My Workout", "🌐 Community Feed"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.rerun()

    if menu == "💪 My Workout":
        selected_date = st.sidebar.date_input("📅 Choose Date", datetime.date.today())
        day_name = selected_date.strftime("%A")
        st.title(f"Workout: {selected_date.strftime('%b %d, %Y')}")

        if selected_date >= datetime.date.today():
            with st.expander("➕ Add New Exercise"):
                ex_name = st.text_input("Exercise Name")
                upload_method = st.radio("Media Source", ["Camera", "Gallery", "Video"], horizontal=True)
                uploaded_file = None
                m_type = "image"

                if upload_method == "Camera":
                    if st.checkbox("Open Camera"):
                        uploaded_file = st.camera_input("Take a photo")
                elif upload_method == "Gallery":
                    uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
                else: 
                    uploaded_file = st.file_uploader("Upload Video", type=['mp4'])
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
        workouts = db.get_workouts(st.session_state.user_id, selected_date)
        if not workouts:
            st.info("No exercises found for this date. 💪")
        
        for wid, wname, wpath, wtype in workouts:
            with st.expander(f"⚙️ {wname.upper()}", expanded=True):
                col_media, col_data = st.columns([1, 1])
                with col_media:
                    if wpath and os.path.exists(wpath):
                        if wtype == "video": st.video(wpath)
                        else: st.image(wpath, use_container_width=True)
                
                with col_data:
                    with st.form(f"set_form_{wid}"):
                        sn = st.number_input("Set Number", min_value=1, step=1, key=f"s{wid}")
                        sr = st.number_input("Reps", min_value=1, step=1, key=f"r{wid}")
                        sw = st.number_input("Weight (kg)", min_value=0.0, step=2.5, key=f"w{wid}")
                        if st.form_submit_button("💾 SAVE SET"):
                            db.add_set(wid, sn, sw, sr)
                            st.rerun()
                    
                    sets = db.get_sets(wid)
                    for s_num, s_w, s_r in sets:
                        st.write(f"✅ **Set {s_num}:** {s_w}kg × {s_r}")

                if st.button(f"🗑️ Delete ", key=f"del{wid}", use_container_width=True):
                    db.delete_workout(wid)
                    st.rerun()

    elif menu == "🌐 Community Feed":
        render_community_feed()
