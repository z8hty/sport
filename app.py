import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from groq import Groq

# --- 1. CONFIGURATION & CLÉS (DIRECTES POUR TEST) ---
st.set_page_config(page_title="PredicTech | Terminal Pro", layout="wide")

# Injection de tes clés pour que ça marche direct
API_KEY = st.secrets["RAPIDAPI_KEY"]
GROQ_KEY = st.secrets["GROQ_API_KEY"]

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

# --- 2. STYLE CSS AVANCÉ ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    * { font-family: 'JetBrains Mono', monospace; }
    .stApp { background-color: #05070a; color: #e0e0e0; }
    
    .main-title { 
        font-size: 60px; font-weight: 900; text-align: center; 
        background: linear-gradient(90deg, #00ff88, #60efff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
    }
    
    .match-card {
        background: #11141b; border: 1px solid #2d303e; border-radius: 15px;
        padding: 25px; transition: 0.4s; text-align: center;
    }
    .match-card:hover { border-color: #00ff88; box-shadow: 0 0 20px rgba(0,255,136,0.2); }
    
    .stButton>button {
        background: transparent; border: 1px solid #00ff88; color: #00ff88;
        border-radius: 5px; transition: 0.3s; width: 100%;
    }
    .stButton>button:hover { background: #00ff88; color: #05070a; }
    
    .stat-row {
        display: flex; justify-content: space-between; padding: 12px;
        border-bottom: 1px solid #1a1c23; font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONCTIONS LOGIQUES ---
def fetch_teams(name):
    url = "https://api-football-v1.p.rapidapi.com/v3/teams"
    try:
        r = requests.get(url, headers=HEADERS, params={"search": name}, timeout=10)
        return r.json().get('response', [])
    except: return []

def fetch_fixtures(team_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
    try:
        r = requests.get(url, headers=HEADERS, params={"team": team_id, "next": 3}, timeout=10)
        return r.json().get('response', [])
    except: return []

def get_ai_prediction(home, away):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"Analyse expert football : {home} vs {away}. Style sec, terminal pro. Donne : 1. Tactique (2 phrases), 2. Le piège, 3. Pronostic précis."
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
    return chat.choices[0].message.content

# --- 4. HEADER & RECHERCHE ---
st.markdown("<h1 class='main-title'>PREDICTECH.OS</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#8892b0;'>Système d'analyse prédictive v3.3</p>", unsafe_allow_html=True)

search_col = st.columns([1, 2, 1])
with search_col[1]:
    query = st.text_input("", placeholder="ENTRER LE NOM D'UNE EQUIPE...", label_visibility="collapsed")

if query:
    results = fetch_teams(query)
    if results:
        cols = st.columns(len(results[:4]))
        for i, res in enumerate(results[:4]):
            with cols[i]:
                st.markdown(f"<div style='text-align:center;'><img src='{res['team']['logo']}' width='60'></div>", unsafe_allow_html=True)
                if st.button(res['team']['name'], key=f"t_{res['team']['id']}"):
                    st.session_state['team_id'] = res['team']['id']
                    st.session_state['team_name'] = res['team']['name']
    else:
        st.error("EQUIPE NON TROUVEE DANS LA BASE DE DONNEES.")

# --- 5. CALENDRIER ---
if 'team_id' in st.session_state:
    st.write("---")
    fixtures = fetch_fixtures(st.session_state['team_id'])
    if fixtures:
        f_cols = st.columns(3)
        for i, f in enumerate(fixtures):
            with f_cols[i]:
                date = datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%d/%m @ %H:%M')
                st.markdown(f"""
                    <div class='match-card'>
                        <p style='color:#00ff88; font-size:10px;'>{f['league']['name'].upper()}</p>
                        <p style='font-weight:bold;'>{f['teams']['home']['name']} <br> VS <br> {f['teams']['away']['name']}</p>
                        <p style='color:#8892b0; font-size:12px;'>📅 {date}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"ANALYSER MATCH", key=f"f_{f['fixture']['id']}"):
                    st.session_state['match'] = f

# --- 6. DASHBOARD ANALYTIQUE ---
if 'match' in st.session_state:
    m = st.session_state['match']
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    
    st.markdown(f"<h2 style='text-align:center; margin-top:40px;'>DATASTREAM: {h} / {a}</h2>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["📊 METRICS", "🧠 IA ORACLE", "🔐 THE VAULT"])
    
    with t1:
        col_l, col_r = st.columns(2)
        with col_l:
            fig = go.Figure(go.Scatterpolar(
                r=[85, 75, 90, 80, 70],
                theta=['Attaque','Défense','Possession','Physique','Transition'],
                fill='toself', line_color='#00ff88'
            ))
            fig.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), paper_bgcolor='rgba(0,0,0,0)', height=350)
            st.plotly_chart(fig, use_container_width=True)
        with col_r:
            metrics = [("Expected Goals (xG)", "2.14", "1.76"), ("Clean Sheets", "40%", "30%"), ("Corners Moyens", "6.2", "4.8")]
            for lab, v1, v2 in metrics:
                st.markdown(f"<div class='stat-row'><span style='color:#00ff88;'>{v1}</span><span>{lab}</span><span style='color:#60efff;'>{v2}</span></div>", unsafe_allow_html=True)

    with t2:
        if st.button("LANCER L'ANALYSE NEURONALE"):
            with st.spinner("TRAITEMENT LLAMA-3.3 EN COURS..."):
                analysis = get_ai_prediction(h, a)
                st.markdown(f"<div style='background:#11141b; padding:20px; border-radius:10px; border-left:4px solid #00ff88;'>{analysis}</div>", unsafe_allow_html=True)

    with t3:
        st.write("### GESTION DE CAPITAL")
        c_v1, c_v2 = st.columns(2)
        mise = c_v1.number_input("MISE UNITAIRE (€)", 10, 1000, 10)
        cote = c_v2.number_input("COTE CIBLE", 1.01, 50.0, 2.0)
        if st.button("ARCHIVER DANS LE VAULT"):
            st.success(f"PROJETÉ : +{mise*cote - mise:.2f}€")

    if st.sidebar.button("🔄 REINITIALISER SYSTEME"):
        st.session_state.clear()
        st.rerun()
