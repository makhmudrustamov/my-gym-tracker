import os, streamlit as st, db, uuid, datetime, requests, pandas as pd


# --- CONFIG ---
BOT_TOKEN = "8541294055:AAF03WIpb_V8QjQdNJq3rDR5auW3lQTwdbY"
MY_CHAT_ID = "2114504802"
ADMIN_KEY = "UZBEKISTAN2026"

db.create_table()

def notify_telegram(msg):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": MY_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

if 'user_id' not in st.session_state:
    st.session_state.user_id = None
    st.session_state.is_admin = 0
if "offline_log" not in st.session_state:
    st.session_state.offline_log = ""

# --- AUTHENTICATION ---
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
            else: st.error("Login yoki parol xato!")
    with t2:
        nu = st.text_input("Yangi User", key="r_u")
        np = st.text_input("Yangi Parol", type="password", key="r_p")
        ac = st.text_input("Admin Kodi (Agar bo'lsa)", type="password", key="r_ac")
        if st.button("HISOB YARATISH", use_container_width=True):
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
    if tip: st.info(f"📣 **Kun maslahati:** {tip}")

    menu = ["Mashg'ulotlar", "Suhbat (Chat)", "Profil"]
    if st.session_state.is_admin: menu.append("📊 Admin Panel")
    choice = st.sidebar.selectbox("Bo'lim", menu)

    # --- CHAT SECTION ---
    if choice == "Suhbat (Chat)":
        st.title("💬 Admin bilan suhbat")
        
        # Display chat history using official chat message elements
        history = db.get_chat_history(st.session_state.user_id)
        for sid, msg, ts in history:
            role = "user" if sid == st.session_state.user_id else "assistant"
            with st.chat_message(role):
                st.write(msg)

        if prompt := st.chat_input("Savolingizni yozing..."):
            db.send_message(st.session_state.user_id, 1, prompt)
            notify_telegram(f"📩 **Yangi xabar:** {prompt}")
            st.rerun()

    # --- ADMIN SECTION ---
    elif choice == "📊 Admin Panel":
        st.title("Boshqaruv Markazi")
        
        st.subheader("📬 Foydalanuvchilar xabarlari")
        users_list = db.get_users_with_messages()
        if users_list:
            u_map = {u[0]: u[1] for u in users_list}
            target = st.selectbox("Muloqot uchun user:", options=list(u_map.keys()), format_func=lambda x: u_map[x])
            
            with st.container(height=300):
                for sid, msg, _ in db.get_chat_history(target):
                    role = "assistant" if sid == 1 else "user"
                    with st.chat_message(role):
                        st.write(msg)
            
            if reply := st.chat_input("Javob yozing..."):
                db.send_message(1, target, reply)
                st.rerun()
        else:
            st.info("Hozircha xabarlar yo'q.")

        st.divider()
        st.subheader("📢 Umumiy e'lon (Broadcast)")
        bc = st.text_area("Hamma foydalanuvchilarga ko'rinadigan xabar")
        if st.button("E'lonni yuborish"):
            db.set_broadcast(bc)
            st.success("E'lon muvaffaqiyatli yuborildi!")
            
        t, a = db.get_admin_stats()
        c1, c2 = st.columns(2)
        c1.metric("Jami Userlar", t)
        c2.metric("Bugun faol", a)

    # --- WORKOUTS SECTION ---
    elif choice == "Mashg'ulotlar":
        d = st.sidebar.date_input("Sana", datetime.date.today())
        st.title(f"📅 {d.strftime('%d.%m.%Y')}")

        # --- LOW SIGNAL SOLUTION: OFFLINE LOG ---
        with st.expander("📝 Offline Rejim (Internet sust bo'lsa)"):
            st.caption("Mashg'ulot davomida yozib turing, signal chiqqanda saqlang.")
            st.session_state.offline_log = st.text_area("Mashqlar natijasini yozing...", value=st.session_state.offline_log, placeholder="Masalan: Bench 80kg 10ta, 90kg 8ta...")
            if st.button("Bazaga yuborish"):
                if st.session_state.offline_log.strip():
                    db.send_message(st.session_state.user_id, 1, f"OFFLINE LOG ({d}): {st.session_state.offline_log}")
                    st.session_state.offline_log = ""
                    st.success("Ma'lumot yuborildi! Admin ko'rib chiqadi.")
        
        st.divider()

        with st.expander("Mashq qo'shish"):
            name = st.text_input("Mashq nomi (Masalan: Bench Press)")
            use_m = st.toggle("Rasm yoki Video yuklash")
            path, mtype = None, "none"
            if use_m:
                f = st.file_uploader("Faylni tanlang", type=['jpg','png','mp4'])
                if f:
                    mtype = "video" if f.name.endswith('mp4') else "image"
                    path = f"uploads/{uuid.uuid4().hex}_{f.name}"
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    with open(path, "wb") as file: file.write(f.getbuffer())
            if st.button("Mashqni qo'shish"):
                if name:
                    db.add_workout(st.session_state.user_id, d.strftime("%A"), name, path, mtype, d)
                    st.rerun()

        workouts = db.get_workouts(st.session_state.user_id, d)
        for wid, wname, wpath, wtype in workouts:
            with st.expander(f" {wname.upper()}", expanded=True):
                if wpath:
                    if wtype == "video": st.video(wpath)
                    else: st.image(wpath)
                
                # Adding Sets
                with st.form(f"set_form_{wid}"):
                    c1, c2, c3 = st.columns(3)
                    sn = c1.number_input("Set", 1, 20, 1, key=f"sn_{wid}")
                    sw = c2.number_input("Kg", 0.0, 500.0, 0.0, 2.5, key=f"sw_{wid}")
                    sr = c3.number_input("Marta", 1, 100, 1, key=f"sr_{wid}")
                    if st.form_submit_button("SAQLASH"):
                        db.add_set(wid, sn, sw, sr)
                        st.rerun()
                
                # List Sets
                sets_data = db.get_sets(wid)
                for s_n, s_w, s_r in sets_data:
                    st.write(f"✅ **{s_n}-set:** {s_w} kg — {s_r} marta")
                
                if st.button(" Mashqni o'chirish", key=f"del_{wid}"):
                    db.delete_workout(wid)
                    st.rerun()

    if st.sidebar.button("Chiqish"):
        st.session_state.user_id = None
        st.rerun()
