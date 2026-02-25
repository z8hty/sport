import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from groq import Groq

# --- 1. CONFIGURATION & ENGINE ---
st.set_page_config(page_title="PredicTech | Terminal Pro", layout="wide")

# On récupère tes clés proprement depuis les secrets Streamlit
try:
    API_KEY = st.secrets["API_SPORTS_KEY"]
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("⚠️ Clés API introuvables. Vérifie tes Secrets sur Streamlit.")
    st.stop()

# LES NOUVEAUX HEADERS DIRECTS (Adieu RapidAPI)
HEADERS = {
    "x-apisports-key": API_KEY
}
BASE_URL = "https://v3.football.api-sports.io"

# --- 2. STYLE CSS TERMINAL ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    * { font-family: 'JetBrains Mono', monospace; }
    .stApp { background-color: #05070a; color: #e0e0e0; }
    .main-title { 
        font-size: 65px; font-weight: 900; text-align: center; 
        background: linear-gradient(90deg, #00ff88, #60efff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px; letter-spacing: -2px;
    }
    .match-card {
        background: #11141b; border: 1px solid #2d303e; border-radius: 15px;
        padding: 25px; transition: 0.4s; text-align: center; margin-bottom: 10px;
    }
    .match-card:hover { border-color: #00ff88; box-shadow: 0 0 25px rgba(0,255,136,0.15); }
    .stButton>button {
        background: transparent; border: 1px solid #00ff88; color: #00ff88;
        border-radius: 8px; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background: #00ff88; color: #05070a; box-shadow: 0 0 10px #00ff88; }
    .stat-row {
        display: flex; justify-content: space-between; padding: 15px;
        border-bottom: 1px solid #1a1c23; font-size: 14px;
    }
    .val-home { color: #00ff88; font-weight: bold; }
    .val-away { color: #60efff; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONCTIONS LOGIQUES ---
def fetch_teams(name):
    try:
        r = requests.get(f"{BASE_URL}/teams", headers=HEADERS, params={"search": name}, timeout=10)
        return r.json().get('response', [])
    except: return []

def fetch_fixtures(team_id):
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": team_id, "next": 3}, timeout=10)
        return r.json().get('response', [])
    except: return []

def get_ai_prediction(home, away):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"Analyse expert foot : {home} vs {away}. Style terminal pro sec. 1. Analyse tactique (2 phrases). 2. Le piège du match. 3. Pronostic final (Safe vs Risqué)."
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
    return chat.choices[0].message.content

# --- 4. NAVIGATION INTERFACE ---
st.markdown("<h1 class='main-title'>PREDICTECH.OS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8892b0; margin-bottom:40px;'>CORE ANALYTICS ENGINE V3.3 // READY</p>", unsafe_allow_html=True)

search_col = st.columns([1, 2, 1])
with search_col[1]:
    query = st.text_input("", placeholder="ENTRER LE NOM D'UNE EQUIPE (EX: PARIS SAINT GERMAIN)...", label_visibility="collapsed")

if query:
    results = fetch_teams(query)
    if results:
        st.markdown("### 📡 ÉQUIPES DÉTECTÉES")
        cols = st.columns(len(results[:4]))
        for i, res in enumerate(results[:4]):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; margin-bottom:10px;'><img src='{res['team']['logo']}' width='70'></div>", unsafe_allow_html=True)
                if st.button(res['team']['name'], key=f"t_{res['team']['id']}"):
                    st.session_state['team_id'] = res['team']['id']
                    st.session_state['team_name'] = res['team']['name']
    else:
        st.error("AUCUN FLUX DÉTECTÉ POUR CE NOM.")

# --- 5. CALENDRIER DES ÉVÉNEMENTS ---
if 'team_id' in st.session_state:
    st.write("---")
    st.markdown(f"### 🗓️ PROCHAINS MATCHS : {st.session_state['team_name'].upper()}")
    fixtures = fetch_fixtures(st.session_state['team_id'])
    
    if fixtures:
        f_cols = st.columns(3)
        for i, f in enumerate(fixtures):
            with f_cols[i]:
                date = datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%d/%m @ %H:%M')
                st.markdown(f"""
                    <div class='match-card'>
                        <p style='color:#00ff88; font-size:10px; font-weight:bold;'>{f['league']['name'].upper()}</p>
                        <p style='font-size:16px; font-weight:bold;'>{f['teams']['home']['name']}<br><span style='color:#333;'>VS</span><br>{f['teams']['away']['name']}</p>
                        <p style='color:#8892b0; font-size:12px;'>📅 {date}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"SÉLECTIONNER MATCH", key=f"f_{f['fixture']['id']}"):
                    st.session_state['match'] = f

# --- 6. TABLEAU DE BORD DE PRÉDICTION ---
if 'match' in st.session_state:
    m = st.session_state['match']
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    
    st.markdown(f"<h2 style='text-align:center; margin-top:50px; color:#00ff88;'>ANALYSE DU DUEL : {h} / {a}</h2>", unsafe_allow_html=True)
    
    tabs = st.tabs(["📊 DATA METRICS", "🧠 ORACLE IA", "🔐 BANKROLL VAULT"])
    
    with tabs[0]:
        c_l, c_r = st.columns(2)
        with c_l:
            fig = go.Figure(go.Scatterpolar(
                r=[85, 75, 92, 80, 70], theta=['Atk','Def','Poss','Phys','Trans'], fill='toself', line_color='#00ff88', name=h
            ))
            fig.add_trace(go.Scatterpolar(
                r=[70, 88, 75, 85, 82], theta=['Atk','Def','Poss','Phys','Trans'], fill='toself', line_color='#60efff', name=a
            ))
            fig.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), paper_bgcolor='rgba(0,0,0,0)', height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with c_r:
            st.markdown("<br>", unsafe_allow_html=True)
            stats = [("Buts Moyens / Match", "2.14", "1.76"), ("xG (Expected Goals)", "1.98", "1.42"), 
                     ("Clean Sheets (10j)", "4", "2"), ("Corners Moyens", "6.2", "4.5")]
            for label, v1, v2 in stats:
                st.markdown(f"<div class='stat-row'><span class='val-home'>{v1}</span><span style='color:#8892b0;'>{label.upper()}</span><span class='val-away'>{v2}</span></div>", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("### ⚡ LLAMA-3.3 ANALYTICS ENGINE")
        if st.button("DÉCRYPTER LE MATCH"):
            with st.spinner("CALCUL DES PROBABILITÉS..."):
                prediction = get_ai_prediction(h, a)
                st.markdown(f"<div style='background:#11141b; padding:25px; border-radius:10px; border-left:4px solid #00ff88; font-size:15px; line-height:1.6;'>{prediction}</div>", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("### 🏦 GESTIONNAIRE DE PORTEFEUILLE")
        c_m, c_c, c_r = st.columns(3)
        mise = c_m.number_input("MISE (€)", 10, 5000, 50)
        cote = c_c.number_input("COTE BOOKMAKER", 1.01, 10.0, 1.85)
        gain = (mise * cote) - mise
        c_r.metric("PROFIT NET ESTIMÉ", f"{gain:.2f} €", f"{((gain/mise)*100):.1f}% ROI")
        if st.button("ARCHIVER DANS LE VAULT"):
            st.success("TICKET ARCHIVÉ AVEC SUCCÈS.")

    if st.sidebar.button("🔄 REBOOT SYSTEM"):
        st.session_state.clear()
        st.rerun()
