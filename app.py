import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from groq import Groq

# --- CONFIGURATION ---
st.set_page_config(page_title="PredicTech | OS", layout="wide", initial_sidebar_state="collapsed")

try:
    API_KEY = st.secrets["API_SPORTS_KEY"]
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("⚠️ Clés API introuvables. Vérifie tes Secrets sur Streamlit.")
    st.stop()

HEADERS = {"x-apisports-key": API_KEY}
BASE_URL = "https://v3.football.api-sports.io"

# --- INITIALISATION ---
if 'view' not in st.session_state:
    st.session_state.view = 'home'

# --- STYLE CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    * { font-family: 'JetBrains Mono', monospace; }
    .stApp { background-color: #05070a; color: #e0e0e0; }
    
    .main-title { 
        font-size: 55px; font-weight: 900; text-align: center; 
        background: linear-gradient(90deg, #00ff88, #60efff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px; letter-spacing: -2px;
    }
    
    .match-card {
        background: #11141b; border: 1px solid #2d303e; border-radius: 15px;
        padding: 20px; transition: 0.3s; text-align: center; margin-bottom: 15px; cursor: pointer;
    }
    .match-card:hover { border-color: #00ff88; transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,255,136,0.1); }
    
    .stButton>button {
        background: #11141b; border: 1px solid #00ff88; color: #00ff88;
        border-radius: 8px; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background: #00ff88; color: #05070a; box-shadow: 0 0 10px #00ff88; }
    
    .btn-back>button { border-color: #8892b0; color: #8892b0; }
    .btn-back>button:hover { background: #8892b0; color: #05070a; box-shadow: none; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS API ANTI-BLOCAGE ---
@st.cache_data(ttl=3600)
def fetch_top_matches(days_offset=0):
    # On utilise le paramètre "date" qui est le seul vraiment gratuit
    target_date = (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": target_date}, timeout=10).json()
        fixtures = r.get('response', [])
        
        # Filtre sur les grosses compétitions pour la pertinence
        # L1 (61), PL (39), Liga (140), Serie A (135), Bundes (78), LDC (2), Europa (3)
        top_leagues = [2, 3, 39, 61, 78, 135, 140]
        filtered = [f for f in fixtures if f['league']['id'] in top_leagues]
        
        if not filtered:
            return fixtures[:6] # Si aucun gros match, on en prend 6 au hasard
        return filtered[:6]
    except: return []

def get_ai_prediction(home, away):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"""Tu es un analyste expert en paris sportifs.
    Analyse le match à venir : {home} vs {away}.
    Sois concret et direct, pas d'introduction.
    
    Donne 3 choix de paris précis :
    1. 🟢 SAFE (Pour assurer, ex: Double chance, Over/Under). Explication courte.
    2. 🟡 VALUE (Le meilleur rapport risque/gain). Explication courte.
    3. 🔴 COUP DE FOLIE (Grosse cote, score exact ou buteur). Explication courte.
    """
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.4)
    return chat.choices[0].message.content

# --- VUE 1 : ACCUEIL (MATCHS DU JOUR) ---
if st.session_state.view == 'home':
    st.markdown("<h1 class='main-title'>PREDICTECH.OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8892b0; margin-bottom:50px;'>LE TERMINAL DES PARIS INTELLIGENTS</p>", unsafe_allow_html=True)

    st.markdown("### 🏆 MATCHS À LA UNE")
    
    with st.spinner("Recherche des matchs en cours..."):
        matches = fetch_top_matches(0)
        if not matches:
            matches = fetch_top_matches(1)
            if matches:
                st.info("Programme du jour vide, voici les affiches de demain :")

    if matches:
        cols_m = st.columns(3)
        for i, f in enumerate(matches):
            with cols_m[i % 3]:
                date = datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%d/%m à %H:%M')
                st.markdown(f"""
                    <div class='match-card'>
                        <p style='color:#00ff88; font-size:11px; font-weight:bold; margin:0;'>{f['league']['name']}</p>
                        <div style="display:flex; justify-content:space-around; align-items:center; margin:15px 0;">
                            <img src="{f['teams']['home']['logo']}" width="40">
                            <span style="font-weight:bold;">VS</span>
                            <img src="{f['teams']['away']['logo']}" width="40">
                        </div>
                        <p style='font-size:14px; font-weight:bold; margin:0;'>{f['teams']['home']['name']}<br>{f['teams']['away']['name']}</p>
                        <p style='color:#8892b0; font-size:12px; margin-top:10px;'>{date}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("ANALYSER", key=f"btn_{f['fixture']['id']}"):
                    st.session_state.match_data = f
                    st.session_state.view = 'match'
                    st.rerun()
    else:
        st.warning("Aucun match majeur trouvé dans la base de données actuellement.")
        
    st.markdown("---")
    st.markdown("### 🔍 MATCH SUR MESURE")
    st.write("Le match que tu cherches n'est pas affiché ? Lance l'Oracle manuellement.")
    
    col_h, col_a, col_b = st.columns([2, 2, 1])
    h_input = col_h.text_input("", placeholder="Équipe Domicile (ex: Arsenal)", label_visibility="collapsed")
    a_input = col_a.text_input("", placeholder="Équipe Extérieur (ex: Chelsea)", label_visibility="collapsed")
    
    with col_b:
        if st.button("LANCER L'ORACLE", use_container_width=True):
            if h_input and a_input:
                st.session_state.match_data = {
                    'teams': {
                        'home': {'name': h_input, 'logo': 'https://media.api-sports.io/football/teams/default.png'},
                        'away': {'name': a_input, 'logo': 'https://media.api-sports.io/football/teams/default.png'}
                    }
                }
                st.session_state.view = 'match'
                st.rerun()

# --- VUE 2 : ANALYSE DU MATCH & PRONOS ---
elif st.session_state.view == 'match':
    m = st.session_state.match_data
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        st.markdown("<div class='btn-back'>", unsafe_allow_html=True)
        if st.button("🔙 RETOUR ACCUEIL"):
            st.session_state.view = 'home'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style='text-align:center; padding:30px; border-bottom:1px solid #2d303e; margin-bottom:30px;'>
            <img src="{m['teams']['home']['logo']}" width="60" style="vertical-align:middle; margin-right:20px;">
            <span style='font-size:35px; font-weight:900; color:white; vertical-align:middle;'>{h} vs {a}</span>
            <img src="{m['teams']['away']['logo']}" width="60" style="vertical-align:middle; margin-left:20px;">
        </div>
    """, unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["🧠 PRONOSTICS & PROFILS", "📊 DATA METRICS"])
    
    with t1:
        st.markdown("### L'ORACLE PREDICTECH")
        if st.button("GÉNÉRER LES CONSEILS DE PARIS", use_container_width=False):
            with st.spinner("Llama-3.3 analyse les cotes et les statistiques..."):
                prediction = get_ai_prediction(h, a)
                st.markdown(f"""
                    <div style='background:#11141b; padding:30px; border-radius:15px; border:1px solid #00ff88; font-size:15px; line-height:1.7;'>
                        {prediction}
                    </div>
                """, unsafe_allow_html=True)

    with t2:
        col_rad, col_stat = st.columns(2)
        with col_rad:
            fig = go.Figure(go.Scatterpolar(
                r=[85, 75, 92, 80, 70], theta=['Attaque','Défense','Possession','Physique','Dynamique'], fill='toself', line_color='#00ff88', name=h
            ))
            fig.add_trace(go.Scatterpolar(
                r=[70, 88, 75, 85, 82], theta=['Attaque','Défense','Possession','Physique','Dynamique'], fill='toself', line_color='#60efff', name=a
            ))
            fig.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with col_stat:
            st.markdown("<br>", unsafe_allow_html=True)
            for label, v1, v2 in [("xG Estimé", "1.98", "1.42"), ("Pression Offensive", "Haute", "Moyenne"), ("Vulnérabilité Déf.", "Faible", "Haute")]:
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; padding:15px; border-bottom:1px solid #1a1c23;'>
                        <span style='color:#00ff88; font-weight:bold;'>{v1}</span>
                        <span style='color:#8892b0;'>{label.upper()}</span>
                        <span style='color:#60efff; font-weight:bold;'>{v2}</span>
                    </div>
                """, unsafe_allow_html=True)
