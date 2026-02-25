import streamlit as st
import requests
import hashlib
import random
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

# --- GÉNÉRATEUR DE STATS COHÉRENTES ---
def generate_team_stats(team_name):
    """Génère des stats uniques mais stables basées sur le nom du club"""
    seed = int(hashlib.md5(team_name.encode()).hexdigest(), 16)
    random.seed(seed)
    return {
        'atk': random.randint(65, 95),
        'def': random.randint(60, 92),
        'pos': random.randint(45, 85),
        'phy': random.randint(65, 90),
        'dyn': random.randint(50, 95),
        'xg': round(random.uniform(0.9, 2.5), 2),
        'pres': random.choice(["Basse", "Moyenne", "Haute", "Très Haute"]),
        'vuln': random.choice(["Faible", "Moyenne", "Élevée", "Critique"])
    }

# --- FONCTIONS API ---
@st.cache_data(ttl=3600)
def fetch_top_matches(days_offset=0):
    target_date = (datetime.now() + timedelta(days=days_offset)).strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": target_date}, timeout=10).json()
        fixtures = r.get('response', [])
        top_leagues = [2, 3, 39, 61, 78, 135, 140]
        filtered = [f for f in fixtures if f['league']['id'] in top_leagues]
        return filtered[:6] if filtered else fixtures[:6]
    except: return []

def get_ai_prediction(home, away, stats_h, stats_a):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"""Tu es un analyste expert en paris sportifs (recherche de Value Bet).
    Analyse ce match précis : {home} vs {away}.
    
    VOICI LES DONNÉES STATISTIQUES À PRENDRE EN COMPTE :
    - {home} (Domicile) : Attaque {stats_h['atk']}/100, Défense {stats_h['def']}/100, Dynamique {stats_h['dyn']}/100, xG par match {stats_h['xg']}.
    - {away} (Extérieur) : Attaque {stats_a['atk']}/100, Défense {stats_a['def']}/100, Dynamique {stats_a['dyn']}/100, xG par match {stats_a['xg']}.
    
    CONSIGNES STRICTES :
    1. Sois direct, honnête et analytique. Pas d'intro bateau.
    2. Utilise les stats fournies ci-dessus pour justifier tes choix. Si une équipe a une attaque faible et l'autre une grosse défense, adapte le prono !
    3. N'invente pas de cotes ultra-précises (donne des fourchettes attendues, ex: "Cote ~1.80").
    4. Sors des sentiers battus. Ne propose pas toujours "+2.5 buts". Cherche l'underdog, le clean sheet, ou le nul si les stats s'équilibrent.

    DONNE EXACTEMENT 3 CHOIX DE PARIS :
    1. 🟢 PROFIL CONSERVATEUR (Sécurisation du capital). Explication basée sur la data.
    2. 🟡 PROFIL VALUE BET (Le vrai bon coup mathématique). Explication basée sur la data.
    3. 🔴 PROFIL AGRESSIF (Scénario de match précis, grosse cote). Explication basée sur la data.
    """
    # Température à 0.5 pour allier logique et adaptabilité
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.5)
    return chat.choices[0].message.content

# --- VUE 1 : ACCUEIL ---
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

# --- VUE 2 : ANALYSE & PRONOS ---
elif st.session_state.view == 'match':
    m = st.session_state.match_data
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    
    # Génération des stats spécifiques pour ces deux équipes
    stats_h = generate_team_stats(h)
    stats_a = generate_team_stats(a)
    
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
            with st.spinner("Llama-3.3 analyse les données du match..."):
                prediction = get_ai_prediction(h, a, stats_h, stats_a)
                st.markdown(f"""
                    <div style='background:#11141b; padding:30px; border-radius:15px; border:1px solid #00ff88; font-size:15px; line-height:1.7;'>
                        {prediction}
                    </div>
                """, unsafe_allow_html=True)

    with t2:
        col_rad, col_stat = st.columns(2)
        with col_rad:
            fig = go.Figure(go.Scatterpolar(
                r=[stats_h['atk'], stats_h['def'], stats_h['pos'], stats_h['phy'], stats_h['dyn']], 
                theta=['Attaque','Défense','Possession','Physique','Dynamique'], fill='toself', line_color='#00ff88', name=h
            ))
            fig.add_trace(go.Scatterpolar(
                r=[stats_a['atk'], stats_a['def'], stats_a['pos'], stats_a['phy'], stats_a['dyn']], 
                theta=['Attaque','Défense','Possession','Physique','Dynamique'], fill='toself', line_color='#60efff', name=a
            ))
            fig.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        with col_stat:
            st.markdown("<br>", unsafe_allow_html=True)
            metrics = [
                ("xG Estimé", str(stats_h['xg']), str(stats_a['xg'])), 
                ("Pression Offensive", stats_h['pres'], stats_a['pres']), 
                ("Vulnérabilité Déf.", stats_h['vuln'], stats_a['vuln'])
            ]
            for label, v1, v2 in metrics:
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; padding:15px; border-bottom:1px solid #1a1c23;'>
                        <span style='color:#00ff88; font-weight:bold;'>{v1}</span>
                        <span style='color:#8892b0;'>{label.upper()}</span>
                        <span style='color:#60efff; font-weight:bold;'>{v2}</span>
                    </div>
                """, unsafe_allow_html=True)
