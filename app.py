import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
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

# --- INITIALISATION DE L'ÉTAT ---
if 'view' not in st.session_state:
    st.session_state.view = 'search'

# --- STYLE CSS (On garde ce que tu kiffes) ---
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
    
    .club-header {
        display: flex; align-items: center; justify-content: center; gap: 20px;
        background: linear-gradient(180deg, #11141b 0%, #05070a 100%);
        padding: 30px; border-radius: 15px; border: 1px solid #2d303e; margin-bottom: 30px;
    }
    
    .match-card {
        background: #11141b; border: 1px solid #2d303e; border-radius: 15px;
        padding: 20px; transition: 0.3s; text-align: center; margin-bottom: 15px; cursor: pointer;
    }
    .match-card:hover { border-color: #00ff88; transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,255,136,0.1); }
    
    .form-badge {
        display: inline-block; width: 25px; height: 25px; line-height: 25px; 
        border-radius: 4px; text-align: center; font-weight: bold; margin: 0 3px; color: #111;
    }
    .form-w { background-color: #00ff88; }
    .form-d { background-color: #8892b0; }
    .form-l { background-color: #ff4b4b; color: white; }
    
    .stButton>button {
        background: #11141b; border: 1px solid #00ff88; color: #00ff88;
        border-radius: 8px; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background: #00ff88; color: #05070a; box-shadow: 0 0 10px #00ff88; }
    
    .btn-back>button { border-color: #8892b0; color: #8892b0; }
    .btn-back>button:hover { background: #8892b0; color: #05070a; box-shadow: none; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS API AVEC GESTION D'ERREURS ---
@st.cache_data(ttl=3600)
def fetch_teams(name):
    try:
        r = requests.get(f"{BASE_URL}/teams", headers=HEADERS, params={"search": name}, timeout=10).json()
        if r.get('errors') and isinstance(r['errors'], dict) and len(r['errors']) > 0:
            st.error(f"⚠️ Alerte API : {r['errors']}")
            return []
        return r.get('response', [])
    except: return []

@st.cache_data(ttl=1800)
def fetch_club_data(team_id):
    try:
        r_last = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": team_id, "last": 5}, timeout=10).json()
        r_next = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"team": team_id, "next": 4}, timeout=10).json()
        
        # Détection de la limite de requêtes API
        errors = r_last.get('errors', {}) or r_next.get('errors', {})
        if errors and isinstance(errors, dict) and len(errors) > 0:
            return [], [], errors
            
        return r_last.get('response', []), r_next.get('response', []), None
    except Exception as e: 
        return [], [], {"Exception": str(e)}

def get_ai_prediction(home, away):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"""Tu es un analyste expert en paris sportifs (gestion de bankroll, value bet).
    Analyse le duel : {home} vs {away}. 
    Va droit au but, pas d'introduction.
    
    Donne exactement 3 stratégies claires :
    1. 🟢 PROFIL SAFE (Pari très probable pour sécuriser, ex: double chance, over 1.5) + Courte explication factuelle.
    2. 🟡 PROFIL VALUE (Le meilleur ratio risque/gain, le vrai bon coup) + Courte explication.
    3. 🔴 PROFIL COUP DE FOLIE (Gros risque, grosse cote, ex: buteur + score exact) + Courte explication.
    """
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.4)
    return chat.choices[0].message.content

# --- VUE 1 : RECHERCHE ---
if st.session_state.view == 'search':
    st.markdown("<h1 class='main-title'>PREDICTECH.OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8892b0; margin-bottom:50px;'>SYSTÈME D'ANALYSE GLOBALE</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        query = st.text_input("", placeholder="ENTRER UN CLUB (ex: Marseille, Real Madrid)...", label_visibility="collapsed")

    if query:
        results = fetch_teams(query)
        if results:
            cols = st.columns(len(results[:4]))
            for i, res in enumerate(results[:4]):
                with cols[i]:
                    st.markdown(f"<div style='text-align:center; margin-bottom:10px;'><img src='{res['team']['logo']}' width='80'></div>", unsafe_allow_html=True)
                    if st.button(res['team']['name'], key=f"t_{res['team']['id']}"):
                        st.session_state.team_data = res['team']
                        st.session_state.view = 'club'
                        st.rerun()

# --- VUE 2 : PAGE DU CLUB ---
elif st.session_state.view == 'club':
    team = st.session_state.team_data
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        st.markdown("<div class='btn-back'>", unsafe_allow_html=True)
        if st.button("🔙 RECHERCHE"):
            st.session_state.view = 'search'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Header du club
    st.markdown(f"""
        <div class='club-header'>
            <img src="{team['logo']}" width="100">
            <div>
                <h1 style="margin:0; color:white;">{team['name'].upper()}</h1>
                <span style="color:#00ff88;">{team['country']}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.spinner("Téléchargement des données de la base API..."):
        last_matches, next_matches, api_error = fetch_club_data(team['id'])

    # SI L'API EST BLOQUÉE (Quota max)
    if api_error:
        st.error(f"🛑 Blocage API détecté : {api_error}")
        st.info("💡 Explication : Tu as probablement épuisé tes 100 requêtes gratuites du jour à force de faire des tests. Le compteur se remet à zéro à minuit !")
    
    else:
        col_form, col_next = st.columns([1, 2])
        
        with col_form:
            st.markdown("### 📊 ÉTAT DE FORME (5 DERNIERS)")
            if last_matches:
                form_html = ""
                for m in last_matches:
                    goals_home = m['goals']['home']
                    goals_away = m['goals']['away']
                    is_home = m['teams']['home']['id'] == team['id']
                    
                    if goals_home == goals_away:
                        res, color_class = "N", "form-d"
                    elif (is_home and goals_home > goals_away) or (not is_home and goals_away > goals_home):
                        res, color_class = "V", "form-w"
                    else:
                        res, color_class = "D", "form-l"
                        
                    form_html += f"<span class='form-badge {color_class}'>{res}</span>"
                st.markdown(f"<div>{form_html}</div><br>", unsafe_allow_html=True)
                
                for m in reversed(last_matches[-3:]): 
                    st.markdown(f"<p style='font-size:13px; color:#8892b0; margin:0;'>{m['teams']['home']['name']} <b>{m['goals']['home']} - {m['goals']['away']}</b> {m['teams']['away']['name']}</p>", unsafe_allow_html=True)
            else:
                st.write("Données récentes indisponibles (trêve ou fin de saison).")

        with col_next:
            st.markdown("### 🗓️ MATCHS À VENIR")
            if next_matches:
                cols_m = st.columns(2)
                for i, f in enumerate(next_matches[:4]):
                    with cols_m[i%2]:
                        date = datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%d/%m à %H:%M')
                        st.markdown(f"""
                            <div class='match-card'>
                                <p style='color:#00ff88; font-size:11px; font-weight:bold; margin:0;'>{f['league']['name']}</p>
                                <p style='font-size:14px; font-weight:bold; margin:10px 0;'>{f['teams']['home']['name']} <br>vs<br> {f['teams']['away']['name']}</p>
                                <p style='color:#8892b0; font-size:12px; margin:0;'>{date}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        if st.button("ANALYSER CE MATCH", key=f"btn_match_{f['fixture']['id']}"):
                            st.session_state.match_data = f
                            st.session_state.view = 'match'
                            st.rerun()
            else:
                st.info("Aucun match programmé trouvé dans la base pour l'instant.")

# --- VUE 3 : ANALYSE DU MATCH & PRONOS ---
elif st.session_state.view == 'match':
    m = st.session_state.match_data
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        st.markdown("<div class='btn-back'>", unsafe_allow_html=True)
        if st.button("🔙 RETOUR AU CLUB"):
            st.session_state.view = 'club'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style='text-align:center; padding:30px; border-bottom:1px solid #2d303e; margin-bottom:30px;'>
            <img src="{m['teams']['home']['logo']}" width="60" style="vertical-align:middle; margin-right:20px;">
            <span style='font-size:35px; font-weight:900; color:white; vertical-align:middle;'>{h} vs {a}</span>
            <img src="{m['teams']['away']['logo']}" width="60" style="vertical-align:middle; margin-left:20px;">
        </div>
    """, unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["🧠 IA & PROFILS DE PARIEURS", "📊 DATA METRICS"])
    
    with t1:
        st.markdown("### L'ORACLE PREDICTECH")
        if st.button("GÉNÉRER LES CONSEILS DE PARIS", use_container_width=False):
            with st.spinner("Llama-3.3 analyse les dynamiques et les probabilités..."):
                prediction = get_ai_prediction(h, a)
                st.markdown(f"""
                    <div style='background:#11141b; padding:30px; border-radius:15px; border:1px solid #2d303e; font-size:15px; line-height:1.7;'>
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
            for label, v1, v2 in [("xG (Expected Goals)", "1.98", "1.42"), ("Buts encaissés/m", "0.8", "1.2"), ("Fautes moyennes", "11", "14")]:
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; padding:15px; border-bottom:1px solid #1a1c23;'>
                        <span style='color:#00ff88; font-weight:bold;'>{v1}</span>
                        <span style='color:#8892b0;'>{label.upper()}</span>
                        <span style='color:#60efff; font-weight:bold;'>{v2}</span>
                    </div>
                """, unsafe_allow_html=True)
