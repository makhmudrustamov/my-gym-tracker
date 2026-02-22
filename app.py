import os, streamlit as st, db, uuid, datetime, requests

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

# --- AUTH ---
if st.session_state.user_id is None:
    st.title("PR GYM TRACKER 🇺🇿")
    t1, t2 = st.tabs(["KIRISH", "RO'YXATDAN O'TISH"])
    with t1:
        u = st.text_input("Username", key="l_u")
        p = st.text_input("Parol", type="password", key="l_p")
        if st.button("KIRISH", use_container_width=True):
            res = db.login_user(u, p)
            if res:
                st.session_state.user_id, st.session_state.is_admin = res
                st.rerun()
            else: st.error("Xato!")
    with t2:
        nu = st.text_input("Yangi User", key="r_u")
        np = st.text_input("Yangi Parol", type="password", key="r_p")
        ac = st.text_input("Admin Kodi", type="password", key="r_ac")
        if st.button("HISOB YARATISH", use_container_width=True):
            isa = 1 if ac == ADMIN_KEY else 0
            ok, m = db.create_user(nu, np, isa)
            if ok: st.success(m); notify_telegram(f"🆕 Yangi User: {nu}")
            else: st.warning(m)

else:
    db.update_last_seen(st.session_state.user_id)
    menu = ["Mashg'ulotlar", "Suhbat (Chat)", "Profil"]
    if st.session_state.is_admin: menu.append("📊 Admin Panel")
    choice = st.sidebar.selectbox("Menu", menu)

    # --- MASHG'ULOTLAR ---
    if choice == "Mashg'ulotlar":
        d = st.sidebar.date_input("Sana", datetime.date.today())
        st.title(f"📅 {d.strftime('%d.%m.%Y')}")

        # --- SHAXSIY NOTE QISMI ---
        with st.expander("📝 Shaxsiy eslatmalar (Notebook)"):
            note_input = st.text_area("Yangi note yozish...", placeholder="Masalan: Bugun oyoq mashqida ehtiyot bo'lish kerak.")
            if st.button("Note saqlash"):
                if note_input.strip():
                    db.save_user_note(st.session_state.user_id, note_input)
                    st.success("Saqlandi!")
                    st.rerun()
            
            st.divider()
            my_notes = db.get_user_notes(st.session_state.user_id)
            if my_notes:
                for content, date, nid in my_notes:
                    st.caption(f"🕒 {date}")
                    st.info(content)
                    if st.button("O'chirish", key=f"del_note_{nid}"):
                        db.delete_user_note(nid)
                        st.rerun()
            else: st.write("Eslatmalar yo'q.")

        st.divider()
        # Mashq qo'shish...
        with st.expander("➕ Mashq qo'shish"):
            name = st.text_input("Nomi")
            f = st.file_uploader("Media", type=['jpg','png','mp4'])
            if st.button("Qo'shish"):
                path, mtype = None, "none"
                if f:
                    mtype = "video" if f.name.endswith('mp4') else "image"
                    path = f"uploads/{uuid.uuid4().hex}_{f.name}"
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    with open(path, "wb") as file: file.write(f.getbuffer())
                db.add_workout(st.session_state.user_id, d.strftime("%A"), name, path, mtype, d)
                st.rerun()

        for wid, wname, wpath, wtype in db.get_workouts(st.session_state.user_id, d):
            with st.expander(f"🔥 {wname.upper()}", expanded=True):
                if wpath:
                    if wtype == "video": st.video(wpath)
                    else: st.image(wpath)
                with st.form(f"f{wid}", border=False):
                    c1, c2, c3 = st.columns(3)
                    sn = c1.number_input("Set", 1, key=f"s{wid}")
                    sw = c2.number_input("Kg", 0.0, step=2.5, key=f"w{wid}")
                    sr = c3.number_input("Reps", 1, key=f"r{wid}")
                    if st.form_submit_button("SAVE"):
                        db.add_set(wid, sn, sw, sr); st.rerun()
                for s_n, s_w, s_r in db.get_sets(wid):
                    st.write(f"✅ {s_n}-set: {s_w}kg x {s_r}")
                if st.button("🗑️", key=f"d{wid}"):
                    db.delete_workout(wid); st.rerun()

    # --- CHAT ---
    elif choice == "Suhbat (Chat)":
        st.title("💬 Admin bilan bog'lanish")
        chat_box = st.container(height=450, border=False)
        with chat_box:
            for sid, msg, _ in db.get_chat_history(st.session_state.user_id):
                with st.chat_message("user" if sid == st.session_state.user_id else "assistant"):
                    st.write(msg)
        if prompt := st.chat_input("Savolingiz..."):
            db.send_message(st.session_state.user_id, 1, prompt)
            u_info = db.get_user_info(st.session_state.user_id)
            notify_telegram(f"📩 *Xabar:* {u_info[0]}: {prompt}")
            st.rerun()

    # --- PROFIL ---
    elif choice == "Profil":
        st.title("👤 Profil")
        u_name, u_photo, u_date = db.get_user_info(st.session_state.user_id)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(u_photo if u_photo and os.path.exists(u_photo) else "https://www.w3schools.com/howto/img_avatar.png", use_container_width=True)
        with c2:
            st.subheader(u_name)
            st.caption(f"Qo'shilgan: {u_date}")
        
        with st.expander("⚙️ Tahrirlash"):
            nn = st.text_input("Yangi name", value=u_name)
            np = st.file_uploader("Yangi rasm")
            if st.button("Saqlash"):
                path = u_photo
                if np:
                    path = f"uploads/p_{uuid.uuid4().hex}.jpg"
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    with open(path, "wb") as f: f.write(np.getbuffer())
                ok, msg = db.update_profile(st.session_state.user_id, nn, path)
                if ok: st.success(msg); st.rerun()
                else: st.error(msg)
        
        if st.button("Chiqish", use_container_width=True):
            st.session_state.user_id = None; st.rerun()

    # --- ADMIN PANEL ---
    elif choice == "📊 Admin Panel":
        st.title("📊 Admin Panel")
        users = db.get_users_with_messages()
        unread = db.get_unread_counts()
        if users:
            u_map = {u[0]: u[1] for u in users}
            target = st.selectbox("User", options=list(u_map.keys()), format_func=lambda x: f"{u_map[x]} ({unread.get(x,0)})")
            db.mark_as_read(target)
            
            box = st.container(height=400, border=True)
            with box:
                for sid, msg, _ in db.get_chat_history(target):
                    with st.chat_message("assistant" if sid == 1 else "user"): st.write(msg)
            if reply := st.chat_input("Javob..."):
                db.send_message(1, target, reply); st.rerun()
        
        st.divider()
        t, a = db.get_admin_stats()
        st.metric("Jami Foydalanuvchilar", t, f"{a} bugun faol")
