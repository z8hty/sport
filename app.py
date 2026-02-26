import streamlit as st
import requests
import hashlib
import random
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from groq import Groq
import time

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

if 'vault' not in st.session_state:
    st.session_state.vault = pd.DataFrame(columns=["Date", "Match", "Pari", "Cote", "Mise", "Gain Potentiel"])

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
    .prob-bar-bg { background-color: #1a1c23; border-radius: 5px; height: 10px; width: 100%; margin-top: 5px; overflow: hidden; }
    .prob-bar-fill { height: 100%; background: linear-gradient(90deg, #00ff88, #60efff); transition: 1s ease-in-out; }
    
    /* Style pour le Selectbox */
    div[data-baseweb="select"] > div { background-color: #11141b; border-color: #2d303e; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- NOUVELLE MÉTHODE : TÉLÉCHARGEMENT DES LIGUES (INFALLIBLE) ---
@st.cache_data(ttl=3600, show_spinner=False)
def load_all_top_fixtures():
    """Télécharge les matchs des 7 prochains jours par Ligue (impossible à bloquer par l'API)"""
    # L1 (61), PL (39), Liga (140), Serie A (135), Bundes (78), LDC (2), Europa (3)
    leagues = [61, 39, 140, 135, 78, 2, 3] 
    all_matches = []
    
    date_from = datetime.now().strftime("%Y-%m-%d")
    date_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    for lid in leagues:
        try:
            r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={
                "league": lid,
                "season": 2024,
                "from": date_from,
                "to": date_to,
                "timezone": "Europe/Paris"
            }, timeout=5).json()
            if r.get('response'):
                all_matches.extend(r['response'])
            time.sleep(0.3) # Sécurité pour ne pas déclencher le Rate Limit
        except:
            continue
            
    # On filtre pour ne garder que les matchs non joués
    valid_statuses = ['NS', 'TBD', 'PST']
    upcoming = [m for m in all_matches if m['fixture']['status']['short'] in valid_statuses]
    upcoming.sort(key=lambda x: x['fixture']['timestamp'])
    
    return upcoming

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_standings(league_id):
    try:
        r = requests.get(f"{BASE_URL}/standings", headers=HEADERS, params={"league": league_id, "season": 2024}, timeout=10).json()
        return r.get('response', [])
    except: return []

def get_match_odds(fixture_id):
    if fixture_id:
        try:
            r = requests.get(f"{BASE_URL}/odds", headers=HEADERS, params={"fixture": fixture_id}, timeout=5).json()
            if r.get('response'):
                bets = r['response'][0]['bookmakers'][0]['bets'][0]['values']
                return {b['value']: str(b['odd']) for b in bets}
        except: pass
    return {}

# --- CALCUL MATHÉMATIQUE DES STATS ---
def get_fallback_stats(team_name):
    seed = int(hashlib.md5(team_name.encode()).hexdigest(), 16)
    random.seed(seed)
    if team_name in ["Real Madrid", "Manchester City", "Bayern Munich", "Liverpool", "Arsenal"]: atk, df = 90, 85
    elif team_name in ["Paris Saint Germain", "Barcelona", "Inter", "Bayer Leverkusen", "Juventus"]: atk, df = 85, 82
    elif team_name in ["AC Milan", "Tottenham", "Chelsea", "Manchester United", "Borussia Dortmund"]: atk, df = 81, 78
    elif team_name in ["Marseille", "Lille", "Monaco", "Newcastle", "AS Roma", "Benfica"]: atk, df = 77, 75
    else: atk, df = 73, 72

    return {'atk': atk + random.randint(-2, 2), 'def': df + random.randint(-2, 2), 'dyn': random.randint(65, 85), 'xg': round((atk / 100) * 2.2, 2), 'form_str': 'Non dispo'}

def calculate_true_stats(team_id, team_name, standings_data):
    if not standings_data: return get_fallback_stats(team_name)
    try:
        league_standings = standings_data[0]['league']['standings'][0]
        team_data = next((t for t in league_standings if t['team']['id'] == team_id), None)
        
        if team_data and team_data['all']['played'] > 0:
            played = team_data['all']['played']
            goals_for = team_data['all']['goals']['for']
            goals_against = team_data['all']['goals']['against']
            form = team_data.get('form', '')
            
            avg_gf = goals_for / played
            avg_ga = goals_against / played
            
            stats = {}
            stats['atk'] = min(100, int((avg_gf / 2.5) * 100))
            stats['def'] = max(10, min(100, int(100 - ((avg_ga / 2.0) * 100))))
            stats['xg'] = round(avg_gf, 2)
            stats['form_str'] = form
            
            if form:
                score = sum([3 if r == 'W' else 1 if r == 'D' else 0 for r in form])
                max_score = len(form) * 3
                stats['dyn'] = int((score / max_score) * 100) if max_score > 0 else 70
            else:
                stats['dyn'] = 70
            return stats
    except: pass
    return get_fallback_stats(team_name)

def calculate_probabilities(stats_h, stats_a):
    power_h = stats_h['atk'] + stats_h['def'] + stats_h['dyn'] + 10
    power_a = stats_a['atk'] + stats_a['def'] + stats_a['dyn']
    
    if power_h == 0 and power_a == 0: return 33, 34, 33 
    
    diff = power_h - power_a
    prob_h = 45 + (diff * 0.4)
    prob_a = 30 - (diff * 0.4)
    
    prob_h = max(5, min(90, int(prob_h)))
    prob_a = max(5, min(90, int(prob_a)))
    prob_n = 100 - prob_h - prob_a
    
    return prob_h, prob_n, prob_a

def get_ai_prediction(home, away, stats_h, stats_a, odds):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"""Tu es un algorithme de prédiction mathématique de paris sportifs.
    Analyse ce match : {home} vs {away}.
    
    DATA MATHÉMATIQUE PURE :
    - {home} (Dom) : Attaque {stats_h['atk']}/100, Défense {stats_h['def']}/100, Forme {stats_h['dyn']}/100, Buts {stats_h['xg']}.
    - {away} (Ext) : Attaque {stats_a['atk']}/100, Défense {stats_a['def']}/100, Forme {stats_a['dyn']}/100, Buts {stats_a['xg']}.
    
    COTES OFFICIELLES (1X2) : 1 ({odds.get('Home', 'Non dispo')}) | X ({odds.get('Draw', 'Non dispo')}) | 2 ({odds.get('Away', 'Non dispo')})
    
    CONSIGNES STRICTES :
    1. Base-toi UNIQUEMENT sur ces mathématiques.
    2. Si les cotes contredisent les data, signale une "Value Bet".
    3. Sois direct et factuel.

    DONNE 3 CHOIX DE PARIS :
    1. 🟢 PARI MATHÉMATIQUE (Le plus probable).
    2. 🟡 VALUE BET (Meilleur ratio risque/gain).
    3. 🔴 COUP DE POKER STATISTIQUE (Scénario déduit des datas).
    """
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.3)
    return chat.choices[0].message.content

# --- VUE 1 : ACCUEIL ---
if st.session_state.view == 'home':
    st.markdown("<h1 class='main-title'>PREDICTECH.OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8892b0; margin-bottom:40px;'>LE TERMINAL DES PARIS INTELLIGENTS</p>", unsafe_allow_html=True)

    with st.spinner("Synchronisation avec la base de données européenne..."):
        all_matches = load_all_top_fixtures()

    st.markdown("### 🎯 SÉLECTIONNER UN MATCH (7 PROCHAINS JOURS)")
    if all_matches:
        # Création d'un dictionnaire pour le menu déroulant
        match_options = {}
        for m in all_matches:
            date_str = datetime.fromisoformat(m['fixture']['date'].replace('Z','+00:00')).strftime('%d/%m')
            label = f"{date_str} | {m['teams']['home']['name']} vs {m['teams']['away']['name']} ({m['league']['name']})"
            match_options[label] = m

        col_sel, col_btn = st.columns([3, 1])
        selected_match_label = col_sel.selectbox("Choisis une affiche officielle :", options=list(match_options.keys()), index=None, placeholder="Tape le nom d'un club (ex: Marseille)...")
        
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("LANCER L'ORACLE", use_container_width=True):
                if selected_match_label:
                    st.session_state.match_data = match_options[selected_match_label]
                    st.session_state.view = 'match'
                    st.rerun()
                else:
                    st.error("Sélectionne un match dans la liste.")
    else:
        st.error("Impossible de récupérer les matchs. L'API est temporairement indisponible.")

    st.markdown("---")
    st.markdown("### 🏆 MATCHS MAJEURS À VENIR")
    if all_matches:
        cols_m = st.columns(3)
        for i, f in enumerate(all_matches[:6]): # Affiche les 6 matchs les plus imminents
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
                if st.button("ANALYSER CE MATCH", key=f"mbtn_{f['fixture']['id']}"):
                    st.session_state.match_data = f
                    st.session_state.view = 'match'
                    st.rerun()

# --- VUE 2 : ANALYSE & PRONOS ---
elif st.session_state.view == 'match':
    m = st.session_state.match_data
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    h_id, a_id = m['teams']['home']['id'], m['teams']['away']['id']
    fix_id = m['fixture']['id']
    league_id = m['league']['id']
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        st.markdown("<div class='btn-back'>", unsafe_allow_html=True)
        if st.button("🔙 RETOUR ACCUEIL"):
            st.session_state.view = 'home'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with st.spinner("Calcul des mathématiques du match (Classement officiel)..."):
        standings = fetch_standings(league_id)
        stats_h = calculate_true_stats(h_id, h, standings)
        stats_a = calculate_true_stats(a_id, a, standings)
        prob_h, prob_n, prob_a = calculate_probabilities(stats_h, stats_a)
        odds = get_match_odds(fix_id)

    st.markdown(f"""
        <div style='text-align:center; padding:30px; border-bottom:1px solid #2d303e; margin-bottom:30px;'>
            <img src="{m['teams']['home']['logo']}" width="60" style="vertical-align:middle; margin-right:20px;">
            <span style='font-size:35px; font-weight:900; color:white; vertical-align:middle;'>{h} vs {a}</span>
            <img src="{m['teams']['away']['logo']}" width="60" style="vertical-align:middle; margin-left:20px;">
            <p style='color:#00ff88; margin-top:10px; font-size:14px;'>COTES 1X2 : 1 ({odds.get('Home', '-')}) | X ({odds.get('Draw', '-')}) | 2 ({odds.get('Away', '-')})</p>
        </div>
    """, unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["🧠 ORACLE IA", "📊 DATA MATRICES", "🏦 BANKROLL (VAULT)"])
    
    with t1:
        st.markdown("### MOTEUR DE DÉCISION")
        if st.button("LANCER L'ANALYSE MATHÉMATIQUE", use_container_width=False):
            with st.spinner("Llama-3.3 cherche la Value du match..."):
                prediction = get_ai_prediction(h, a, stats_h, stats_a, odds)
                st.markdown(f"""
                    <div style='background:#11141b; padding:30px; border-radius:15px; border:1px solid #00ff88; font-size:15px; line-height:1.7;'>
                        {prediction}
                    </div>
                """, unsafe_allow_html=True)

    with t2:
        col_rad, col_stat = st.columns(2)
        with col_rad:
            fig = go.Figure(go.Scatterpolar(
                r=[stats_h['atk'], stats_h['def'], stats_h['dyn'], 50, stats_h['atk']], 
                theta=['Attaque','Défense','Forme','Structure','Attaque'], fill='toself', line_color='#00ff88', name=h
            ))
            fig.add_trace(go.Scatterpolar(
                r=[stats_a['atk'], stats_a['def'], stats_a['dyn'], 50, stats_a['atk']], 
                theta=['Attaque','Défense','Forme','Structure','Attaque'], fill='toself', line_color='#60efff', name=a
            ))
            fig.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
        with col_stat:
            st.markdown("### 🎯 MATRICE DE VICTOIRE")
            st.markdown(f"**{h}** ({prob_h}%)")
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_h}%;'></div></div>", unsafe_allow_html=True)
            
            st.markdown(f"<br>**Nul** ({prob_n}%)", unsafe_allow_html=True)
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_n}%; background:linear-gradient(90deg, #8892b0, #4f5b7d);'></div></div>", unsafe_allow_html=True)
            
            st.markdown(f"<br>**{a}** ({prob_a}%)", unsafe_allow_html=True)
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_a}%; background:linear-gradient(90deg, #ff4b4b, #ff8c8c);'></div></div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color:#2d303e;'>", unsafe_allow_html=True)
            
            metrics = [
                ("Moy. Buts par Match", str(stats_h['xg']), str(stats_a['xg'])), 
                ("Série en cours", stats_h['form_str'][-5:] if stats_h['form_str'] else "N/A", stats_a['form_str'][-5:] if stats_a['form_str'] else "N/A")
            ]
            for label, v1, v2 in metrics:
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #1a1c23;'>
                        <span style='color:#00ff88; font-weight:bold; font-size:13px;'>{v1}</span>
                        <span style='color:#8892b0; font-size:12px;'>{label.upper()}</span>
                        <span style='color:#60efff; font-weight:bold; font-size:13px;'>{v2}</span>
                    </div>
                """, unsafe_allow_html=True)

    with t3:
        st.markdown("### 🏦 ARCHIVER UN PARI")
        c1, c2, c3, c4 = st.columns(4)
        pari_nom = c1.text_input("Pari (ex: Victoire OM)", "")
        pari_cote = c2.number_input("Cote", min_value=1.01, value=1.85, step=0.05)
        pari_mise = c3.number_input("Mise (€)", min_value=1, value=10, step=5)
        
        with c4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("SAUVEGARDER LE TICKET", use_container_width=True):
                if pari_nom:
                    new_bet = {
                        "Date": datetime.now().strftime("%d/%m/%Y"),
                        "Match": f"{h} vs {a}",
                        "Pari": pari_nom,
                        "Cote": pari_cote,
                        "Mise": pari_mise,
                        "Gain Potentiel": round(pari_mise * pari_cote, 2)
                    }
                    st.session_state.vault = pd.concat([st.session_state.vault, pd.DataFrame([new_bet])], ignore_index=True)
                    st.success("Pari archivé dans le Vault !")
                else:
                    st.error("Précise le nom du pari.")
        
        st.markdown("---")
        st.markdown("### 📊 HISTORIQUE DU VAULT")
        if not st.session_state.vault.empty:
            st.dataframe(st.session_state.vault, use_container_width=True, hide_index=True)
            
            total_mise = st.session_state.vault['Mise'].sum()
            total_gain = st.session_state.vault['Gain Potentiel'].sum()
            
            c_res1, c_res2 = st.columns(2)
            c_res1.metric("Capital Engagé", f"{total_mise} €")
            c_res2.metric("Retour Potentiel Maximum", f"{total_gain} €", f"+{round(total_gain - total_mise, 2)} € de bénef")
        else:
            st.info("Aucun pari enregistré pour le moment.")
