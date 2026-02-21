import os, streamlit as st, db, uuid, datetime, requests, pandas as pd

# --- CONFIG ---
BOT_TOKEN = "8541294055:AAF03WIpb_V8QjQdNJq3rDR5auW3lQTwdbY"
MY_CHAT_ID = "2114504802"
ADMIN_KEY = "UZB_PR_2024"

db.create_table()

def notify_telegram(msg):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": MY_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

if 'user_id' not in st.session_state:
    st.session_state.user_id = None
    st.session_state.is_admin = 0

# --- AUTHENTICATION ---
if st.session_state.user_id is None:
    st.title("PR GYM TRACKER 🇺🇿")
    t1, t2 = st.tabs(["KIRISH", "RO'YXATDAN O'TISH"])
    with t1:
        u = st.text_input("Username", key="l_u")
        p = st.text_input("Parol", type="password", key="l_p")
        if st.button("KIRISH"):
            res = db.login_user(u, p)
            if res:
                st.session_state.user_id, st.session_state.is_admin = res
                st.rerun()
            else: st.error("Login xato!")
    with t2:
        nu = st.text_input("Yangi User", key="r_u")
        np = st.text_input("Yangi Parol", type="password", key="r_p")
        ac = st.text_input("Admin Kodi", type="password", key="r_ac")
        if st.button("HISOB YARATISH"):
            isa = 1 if ac == ADMIN_KEY else 0
            ok, m = db.create_user(nu, np, isa)
            if ok:
                st.success(m)
                notify_telegram(f"🆕 Yangi {'Admin' if isa else 'User'}: {nu}")
            else: st.warning(m)

# --- MAIN APP ---
else:
    db.update_last_seen(st.session_state.user_id)
    
    tip = db.get_latest_broadcast()
    if tip: st.info(f"📣 {tip}")

    menu = ["Mashg'ulotlar", "Suhbat (Chat)", "Profil"]
    if st.session_state.is_admin: menu.append("📊 Admin Panel")
    choice = st.sidebar.selectbox("Bo'lim", menu)

    # --- CHAT SECTION ---
    if choice == "Suhbat (Chat)":
        st.title("💬 Admin bilan suhbat")
        
        # Pull history safely
        try:
            history = db.get_chat_history(st.session_state.user_id)
            for sid, msg, ts in history:
                role = "user" if sid == st.session_state.user_id else "assistant"
                with st.chat_message(role):
                    st.write(msg)
        except Exception as e:
            st.error("Chat tizimida xato. Admin bilan bog'laning.")

        if prompt := st.chat_input("Savolingizni yozing..."):
            db.send_message(st.session_state.user_id, 1, prompt)
            notify_telegram(f"📩 **Xabar:** {prompt}")
            st.rerun()

    # --- ADMIN SECTION ---
    elif choice == "📊 Admin Panel":
        st.title("Boshqaruv Markazi")
        
        st.subheader("📬 Xabarlar")
        users_list = db.get_users_with_messages()
        if users_list:
            u_map = {u[0]: u[1] for u in users_list}
            target = st.selectbox("Foydalanuvchini tanlang", options=list(u_map.keys()), format_func=lambda x: u_map[x])
            
            with st.container(height=300):
                for sid, msg, _ in db.get_chat_history(target):
                    role = "assistant" if sid == 1 else "user"
                    with st.chat_message(role):
                        st.write(msg)
            
            if reply := st.chat_input("Javob..."):
                db.send_message(1, target, reply)
                st.rerun()
        else:
            st.info("Xabarlar yo'q.")

        st.divider()
        bc = st.text_area("Hamma uchun maslahat")
        if st.button("Yuborish"):
            db.set_broadcast(bc)
            st.success("Yuborildi!")
            
        t, a = db.get_admin_stats()
        st.metric("Jami Userlar", t, f"{a} bugun faol")

    # --- WORKOUTS SECTION ---
    elif choice == "Mashg'ulotlar":
        d = st.sidebar.date_input("Sana", datetime.date.today())
        st.title(f"{d.strftime('%d.%m.%Y')}")
        
        with st.expander("➕ Mashq qo'shish"):
            name = st.text_input("Mashq nomi")
            use_m = st.toggle("Media")
            path, mtype = None, "none"
            if use_m:
                f = st.file_uploader("Fayl", type=['jpg','mp4'])
                if f:
                    mtype = "video" if f.name.endswith('mp4') else "image"
                    path = f"uploads/{uuid.uuid4().hex}_{f.name}"
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    with open(path, "wb") as file: file.write(f.getbuffer())
            if st.button("Saqlash"):
                if name:
                    db.add_workout(st.session_state.user_id, d.strftime("%A"), name, path, mtype, d)
                    st.rerun()

        for wid, wname, wpath, wtype in db.get_workouts(st.session_state.user_id, d):
            with st.expander(f"🏋️ {wname.upper()}", expanded=True):
                if wpath:
                    c1, c2 = st.columns([1,1])
                    with c1:
                        if wtype == "video": st.video(wpath)
                        else: st.image(wpath)
                    target = c2
                else: target = st.container()
                
                with target:
                    with st.form(f"f{wid}"):
                        cols = st.columns(3)
                        sn = cols[0].number_input("Set", 1, key=f"s{wid}")
                        sw = cols[1].number_input("Kg", 0.0, step=2.5, key=f"w{wid}")
                        sr = cols[2].number_input("Marta", 1, key=f"r{wid}")
                        if st.form_submit_button("SAVE"):
                            db.add_set(wid, sn, sw, sr)
                            st.rerun()
                    for s_n, s_w, s_r in db.get_sets(wid):
                        st.write(f"✅ {s_n}-set: {s_w}kg x {s_r}")
                
                if st.button("🗑️ O'chirish", key=f"del{wid}"):
                    db.delete_workout(wid)
                    st.rerun()

    if st.sidebar.button("Chiqish"):
        st.session_state.user_id = None
        st.rerun()
