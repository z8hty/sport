import streamlit as st
import requests
import hashlib
import random
import plotly.graph_objects as go
from datetime import datetime, timedelta
from groq import Groq
import time
import math

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

# Compétitions majeures du catalogue
TOP_LEAGUES = {
    2: "🇪🇺 Champions League",
    3: "🇪🇺 Europa League",
    39: "🇬🇧 Premier League",
    61: "🇫🇷 Ligue 1",
    78: "🇩🇪 Bundesliga",
    135: "🇮🇹 Serie A",
    140: "🇪🇸 La Liga"
}

if 'view' not in st.session_state:
    st.session_state.view = 'home'

# --- STYLE CSS TERMINAL PRO ---
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
        padding: 20px; transition: 0.3s; text-align: center; margin-bottom: 15px;
    }
    .match-card:hover { border-color: #00ff88; transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,255,136,0.1); }
    .stButton>button {
        background: #11141b; border: 1px solid #00ff88; color: #00ff88;
        border-radius: 8px; transition: 0.3s; width: 100%; font-weight: bold;
    }
    .stButton>button:hover { background: #00ff88; color: #05070a; box-shadow: 0 0 10px #00ff88; }
    .btn-back>button { border-color: #8892b0; color: #8892b0; }
    .btn-back>button:hover { background: #8892b0; color: #05070a; box-shadow: none; }
    .league-header { font-size: 20px; font-weight: bold; color: #60efff; border-bottom: 1px solid #2d303e; padding-bottom: 10px; margin-top: 30px; margin-bottom: 20px; text-transform: uppercase; }
    .prob-bar-bg { background-color: #1a1c23; border-radius: 5px; height: 10px; width: 100%; margin-top: 5px; overflow: hidden; }
    .prob-bar-fill { height: 100%; background: linear-gradient(90deg, #00ff88, #60efff); transition: 1s ease-in-out; }
    .team-stats-box { background: #11141b; border: 1px solid #2d303e; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 15px; }
    .stat-number { font-size: 24px; font-weight: bold; color: #00ff88; }
    .value-badge { background: rgba(0, 255, 136, 0.1); color: #00ff88; border: 1px solid #00ff88; padding: 5px 15px; border-radius: 20px; font-size: 14px; font-weight: bold; display: block; margin: 15px auto; width: fit-content; text-align: center;}
    .h2h-box { background: #1a1c23; padding: 10px; border-radius: 8px; font-size: 13px; text-align: center; margin-bottom: 5px;}
    
    div[data-testid="stNumberInput"] input {
        background-color: #ffffff !important;
        color: #05070a !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        border: 2px solid #00ff88 !important;
        border-radius: 8px !important;
        text-align: center !important;
    }
    div[data-testid="stNumberInput"] label p {
        color: #e0e0e0 !important;
        font-weight: bold !important;
        font-size: 14px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- OUTILS DE FORMATAGE ET MATHS ---
def format_form(form_string):
    if not form_string or form_string == 'Non dispo': return "N/A"
    form_string = form_string[-5:]
    return form_string.replace('W', '🟢').replace('D', '⚪').replace('L', '🔴')

def poisson_prob(lmbda, k):
    return (math.exp(-lmbda) * (lmbda**k)) / math.factorial(k)

def calculate_goals_probabilities(xg_h, xg_a):
    prob_h = [poisson_prob(xg_h, i) for i in range(6)]
    prob_a = [poisson_prob(xg_a, i) for i in range(6)]
    btts_yes = (1 - prob_h[0]) * (1 - prob_a[0])
    under_25 = (prob_h[0]*prob_a[0]) + (prob_h[1]*prob_a[0]) + (prob_h[0]*prob_a[1]) + \
               (prob_h[1]*prob_a[1]) + (prob_h[2]*prob_a[0]) + (prob_h[0]*prob_a[2])
    return int((1 - under_25) * 100), int(btts_yes * 100)

# --- MOTEUR CATALOGUE (SÉCURITÉ CACHE AJOUTÉE) ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_daily_catalog_final(date_str):
    time.sleep(0.3)
    r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": date_str, "timezone": "Europe/Paris"}, timeout=10).json()
    if r.get('errors'): raise Exception("API Limit Hit")
    fixtures = r.get('response', [])
    valid_statuses = ['NS', 'TBD', 'PST']
    filtered = [f for f in fixtures if f['league']['id'] in TOP_LEAGUES.keys() and f['fixture']['status']['short'] in valid_statuses]
    filtered.sort(key=lambda x: x['fixture']['timestamp'])
    return filtered

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_standings_final(league_id, season):
    time.sleep(0.3)
    r = requests.get(f"{BASE_URL}/standings", headers=HEADERS, params={"league": league_id, "season": season}, timeout=10).json()
    # On interdit la mise en cache si l'API bloque la requête !
    if r.get('errors'): raise Exception("API Limit Hit")
    return r.get('response', [])

def get_match_odds(fixture_id):
    if fixture_id:
        try:
            r = requests.get(f"{BASE_URL}/odds", headers=HEADERS, params={"fixture": fixture_id}, timeout=5).json()
            if r.get('response'):
                bets = r['response'][0]['bookmakers'][0]['bets'][0]['values']
                return {b['value']: str(b['odd']) for b in bets}
        except: pass
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_h2h_final(team_id_1, team_id_2):
    time.sleep(0.3)
    r = requests.get(f"{BASE_URL}/fixtures/headtohead", headers=HEADERS, params={"h2h": f"{team_id_1}-{team_id_2}", "last": 3}, timeout=5).json()
    if r.get('errors'): raise Exception("API Limit Hit")
    return r.get('response', [])

# --- CALCUL DES STATS ---
def get_fallback_stats(team_name):
    seed = int(hashlib.md5(team_name.encode()).hexdigest(), 16)
    random.seed(seed)
    if team_name in ["Real Madrid", "Manchester City", "Bayern Munich", "Liverpool", "Arsenal"]: atk, df = 90, 85
    elif team_name in ["Paris Saint Germain", "Barcelona", "Inter", "Bayer Leverkusen", "Juventus"]: atk, df = 85, 82
    elif team_name in ["AC Milan", "Tottenham", "Chelsea", "Manchester United", "Borussia Dortmund"]: atk, df = 81, 78
    elif team_name in ["Marseille", "Lille", "Monaco", "Newcastle", "AS Roma", "Benfica", "Lens"]: atk, df = 77, 75
    else: atk, df = 73, 72

    return {'atk': atk + random.randint(-2, 2), 'def': df + random.randint(-2, 2), 'dyn': random.randint(65, 85), 'xg': round((atk / 100) * 2.2, 2), 'form_str': 'Non dispo', 'rank': '-', 'is_fallback': True}

def calculate_true_stats(team_id, team_name, standings_data):
    if not standings_data: return get_fallback_stats(team_name)
    try:
        standings_lists = standings_data[0]['league']['standings']
        team_data = None
        
        for group in standings_lists:
            team_data = next((t for t in group if t['team']['id'] == team_id), None)
            if team_data: break
            
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
            stats['rank'] = str(team_data.get('rank', '-'))
            
            if form:
                score = sum([3 if r == 'W' else 1 if r == 'D' else 0 for r in form])
                max_score = len(form) * 3
                stats['dyn'] = int((score / max_score) * 100) if max_score > 0 else 70
            else:
                stats['dyn'] = 70
                
            stats['is_fallback'] = False
            return stats
    except: pass
    return get_fallback_stats(team_name)

def calculate_probabilities(stats_h, stats_a):
    power_h = stats_h['atk'] + stats_h['def'] + stats_h['dyn'] + 10
    power_a = stats_a['atk'] + stats_a['def'] + stats_a['dyn']
    if power_h == 0 and power_a == 0: return 33, 34, 33 
    
    diff = power_h - power_a
    prob_h = max(5, min(90, int(45 + (diff * 0.4))))
    prob_a = max(5, min(90, int(30 - (diff * 0.4))))
    return prob_h, 100 - prob_h - prob_a, prob_a

def detect_value_bet(prob_h, prob_n, prob_a, odds_dict, home_name, away_name):
    value_msg = ""
    try:
        odd_h = float(odds_dict.get('Home', 0))
        odd_d = float(odds_dict.get('Draw', 0))
        odd_a = float(odds_dict.get('Away', 0))
        
        if odd_h > 0 and odd_h * (prob_h / 100) > 1.05:
            value_msg = f"🔥 VALUE BET DÉTECTÉE : VICTOIRE {home_name.upper()} (Cote {odd_h:.2f})"
        elif odd_a > 0 and odd_a * (prob_a / 100) > 1.05:
            value_msg = f"🔥 VALUE BET DÉTECTÉE : VICTOIRE {away_name.upper()} (Cote {odd_a:.2f})"
        elif odd_d > 0 and odd_d * (prob_n / 100) > 1.10:
            value_msg = f"🔥 VALUE BET DÉTECTÉE : MATCH NUL (Cote {odd_d:.2f})"
    except: pass
    return value_msg

def get_ai_prediction(home, away, stats_h, stats_a, odds, value_msg, h2h_data):
    client = Groq(api_key=GROQ_KEY)
    h2h_text = "Historique récent : " + ", ".join([f"{f['teams']['home']['name']} {f['goals']['home']}-{f['goals']['away']} {f['teams']['away']['name']}" for f in h2h_data]) if h2h_data else "Pas d'historique."

    prompt = f"""Tu es un algorithme de prédiction mathématique de paris sportifs.
    Analyse ce match : {home} vs {away}.
    
    DATA :
    - {home} (Dom) : Classement: {stats_h['rank']}, Attaque {stats_h['atk']}/100, Défense {stats_h['def']}/100, Forme {stats_h['dyn']}/100, Buts/match {stats_h['xg']}.
    - {away} (Ext) : Classement: {stats_a['rank']}, Attaque {stats_a['atk']}/100, Défense {stats_a['def']}/100, Forme {stats_a['dyn']}/100, Buts/match {stats_a['xg']}.
    {h2h_text}
    
    COTES ACTUELLES : 1 ({odds.get('Home', '-')}) | X ({odds.get('Draw', '-')}) | 2 ({odds.get('Away', '-')})
    Mathématiques : {value_msg if value_msg else "Pas de Value flagrante sur le résultat sec."}
    
    CONSIGNES :
    1. Base-toi sur les stats, l'historique et l'enjeu (classement).
    2. Sois direct, factuel et précis. Pas de blabla.
    3. VARIE TES PROPOSITIONS d'un match à l'autre.

    DONNE 3 CHOIX DE PARIS :
    1. 🟢 PARI SAFE : Un pari hyper probable (Double Chance, Over/Under, etc.). Justifie.
    2. 🟡 PARI AUDACIEUX : Une cote intéressante appuyée par la stat dominante (Handicap, Buteur probable, Mi-temps...).
    3. 🔴 COUP DE POKER : Score exact ou scénario pointu basé sur la data.
    """
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.5)
    return chat.choices[0].message.content

# --- INTERFACE ---
def render_match_grid(matches, show_date=False):
    if not matches:
        st.info("Aucun match majeur programmé pour cette période.")
        return

    matches_by_league = {}
    for m in matches:
        lid = m['league']['id']
        if lid not in matches_by_league: matches_by_league[lid] = []
        matches_by_league[lid].append(m)

    for lid, league_matches in matches_by_league.items():
        league_name = TOP_LEAGUES.get(lid, "Compétition")
        st.markdown(f"<div class='league-header'>{league_name}</div>", unsafe_allow_html=True)
        
        cols = st.columns(3)
        for i, f in enumerate(league_matches):
            with cols[i % 3]:
                time_str = datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%d/%m - %H:%M') if show_date else datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%H:%M')
                st.markdown(f"""
                    <div class='match-card'>
                        <div style="display:flex; justify-content:space-around; align-items:center; margin-bottom:15px;">
                            <img src="{f['teams']['home']['logo']}" width="45">
                            <span style="font-weight:bold; color:#8892b0; font-size:12px; background:#1a1c23; padding:4px 8px; border-radius:5px;">{time_str}</span>
                            <img src="{f['teams']['away']['logo']}" width="45">
                        </div>
                        <p style='font-size:15px; font-weight:bold; margin:0;'>{f['teams']['home']['name']}<br><span style="color:#2d303e; font-size:12px;">VS</span><br>{f['teams']['away']['name']}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("ANALYSER LE MATCH", key=f"btn_{f['fixture']['id']}"):
                    st.session_state.match_data = f
                    st.session_state.view = 'match'
                    st.rerun()

# --- VUE 1 : LE CATALOGUE ---
if st.session_state.view == 'home':
    st.markdown("<h1 class='main-title'>PREDICTECH.OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8892b0; margin-bottom:40px;'>CATALOGUE D'ANALYSES ALGORITHMIQUES</p>", unsafe_allow_html=True)

    date_today = datetime.now()
    date_tmrw = date_today + timedelta(days=1)
    date_after = date_today + timedelta(days=2)

    with st.spinner("Synchronisation des vitrines de matchs..."):
        try:
            matches_today = fetch_daily_catalog_final(date_today.strftime("%Y-%m-%d"))
            matches_tmrw = fetch_daily_catalog_final(date_tmrw.strftime("%Y-%m-%d"))
            matches_after = fetch_daily_catalog_final(date_after.strftime("%Y-%m-%d"))
        except:
            matches_today, matches_tmrw, matches_after = [], [], []
            st.warning("⚠️ L'API a bloqué par sécurité (Trop de requêtes rapides). Patiente 30 petites secondes et rafraîchis la page avec F5.")

    upcoming_matches = matches_tmrw + matches_after

    t1, t2 = st.tabs(["🔥 GROSSES AFFICHES (À VENIR)", "📅 MATCHS DU JOUR"])

    with t1:
        render_match_grid(upcoming_matches, show_date=True)
        
    with t2:
        render_match_grid(matches_today, show_date=False)

# --- VUE 2 : ANALYSE ---
elif st.session_state.view == 'match':
    m = st.session_state.match_data
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    h_id, a_id = m['teams']['home']['id'], m['teams']['away']['id']
    fix_id = m['fixture']['id']
    league_id = m['league']['id']
    season_year = m['league']['season']
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        st.markdown("<div class='btn-back'>", unsafe_allow_html=True)
        if st.button("🔙 RETOUR CATALOGUE"):
            st.session_state.view = 'home'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with st.spinner("Extraction des mathématiques et historiques..."):
        try:
            standings = fetch_standings_final(league_id, season_year)
        except:
            standings = []
            
        stats_h = calculate_true_stats(h_id, h, standings)
        stats_a = calculate_true_stats(a_id, a, standings)
        prob_h, prob_n, prob_a = calculate_probabilities(stats_h, stats_a)
        prob_o25, prob_btts = calculate_goals_probabilities(stats_h['xg'], stats_a['xg'])
        api_odds = get_match_odds(fix_id)
        
        try:
            h2h = fetch_h2h_final(h_id, a_id)
        except:
            h2h = []
            
        est_badge = " <span style='font-size:12px; color:#8892b0; font-weight:normal;'>(Stats Estimées)</span>" if stats_h.get('is_fallback') else ""

    st.markdown(f"""
        <div style='text-align:center; padding:30px; border-bottom:1px solid #2d303e; margin-bottom:20px;'>
            <img src="{m['teams']['home']['logo']}" width="60" style="vertical-align:middle; margin-right:20px;">
            <span style='font-size:35px; font-weight:900; color:white; vertical-align:middle;'>{h} vs {a}</span>
            <img src="{m['teams']['away']['logo']}" width="60" style="vertical-align:middle; margin-left:20px;">
        </div>
    """, unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button(f"🔍 VOIR LE PROFIL DE {h.upper()} (Class: {stats_h['rank']})", key="btn_team1"):
            st.session_state.team_data = {'id': h_id, 'name': h, 'logo': m['teams']['home']['logo'], 'stats': stats_h}
            st.session_state.view = 'team_profile'
            st.rerun()
    with col_t2:
        if st.button(f"🔍 VOIR LE PROFIL DE {a.upper()} (Class: {stats_a['rank']})", key="btn_team2"):
            st.session_state.team_data = {'id': a_id, 'name': a, 'logo': m['teams']['away']['logo'], 'stats': stats_a}
            st.session_state.view = 'team_profile'
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)

    t1, t2 = st.tabs(["🧠 L'ORACLE (PRONOSTICS)", "📊 DATA MATRICES"])
    
    with t1:
        st.markdown("### 🎲 COTES DU MATCH (Ajustables)")
        st.markdown("<p style='color:#8892b0; font-size:13px;'>Les cotes de l'API sont pré-remplies. Modifie-les avec tes propres cotes pour recalculer la Value Bet mathématique avant d'interroger l'IA.</p>", unsafe_allow_html=True)
        
        c_odd1, c_odd2, c_odd3 = st.columns(3)
        val_h = float(api_odds['Home']) if api_odds.get('Home') else 0.0
        val_d = float(api_odds['Draw']) if api_odds.get('Draw') else 0.0
        val_a = float(api_odds['Away']) if api_odds.get('Away') else 0.0
        
        man_odd_h = c_odd1.number_input(f"Victoire {h}", value=val_h, min_value=0.0, step=0.05, format="%.2f")
        man_odd_d = c_odd2.number_input(f"Match Nul", value=val_d, min_value=0.0, step=0.05, format="%.2f")
        man_odd_a = c_odd3.number_input(f"Victoire {a}", value=val_a, min_value=0.0, step=0.05, format="%.2f")
        
        final_odds = {
            'Home': f"{man_odd_h:.2f}",
            'Draw': f"{man_odd_d:.2f}",
            'Away': f"{man_odd_a:.2f}"
        }
        
        value_alert = detect_value_bet(prob_h, prob_n, prob_a, final_odds, h, a)
        if value_alert:
            st.markdown(f"<div class='value-badge'>{value_alert}</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("LANCER L'ANALYSE MATHÉMATIQUE", use_container_width=False):
            with st.spinner("Llama-3.3 croise les nouvelles cotes avec les datas..."):
                prediction = get_ai_prediction(h, a, stats_h, stats_a, final_odds, value_alert, h2h)
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
            
            if h2h:
                st.markdown("<p style='color:#60efff; font-weight:bold; margin-top:10px; text-align:center;'>HISTORIQUE DES CONFRONTATIONS</p>", unsafe_allow_html=True)
                for f in h2h:
                    st.markdown(f"<div class='h2h-box'>{f['teams']['home']['name']} <b>{f['goals']['home']} - {f['goals']['away']}</b> {f['teams']['away']['name']}</div>", unsafe_allow_html=True)

        with col_stat:
            st.markdown(f"### 🎯 MATRICE DE VICTOIRE {est_badge}", unsafe_allow_html=True)
            st.markdown(f"**{h}** ({prob_h}%)")
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_h}%;'></div></div>", unsafe_allow_html=True)
            
            st.markdown(f"<br>**Nul** ({prob_n}%)", unsafe_allow_html=True)
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_n}%; background:linear-gradient(90deg, #8892b0, #4f5b7d);'></div></div>", unsafe_allow_html=True)
            
            st.markdown(f"<br>**{a}** ({prob_a}%)", unsafe_allow_html=True)
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_a}%; background:linear-gradient(90deg, #ff4b4b, #ff8c8c);'></div></div>", unsafe_allow_html=True)
            
            st.markdown("<br>### ⚽ PROBABILITÉS DES BUTS (Loi de Poisson)", unsafe_allow_html=True)
            st.markdown(f"**+ de 2.5 Buts** ({prob_o25}%)")
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_o25}%; background:linear-gradient(90deg, #ff9a9e, #fecfef);'></div></div>", unsafe_allow_html=True)
            
            st.markdown(f"<br>**Les 2 équipes marquent** ({prob_btts}%)", unsafe_allow_html=True)
            st.markdown(f"<div class='prob-bar-bg'><div class='prob-bar-fill' style='width:{prob_btts}%; background:linear-gradient(90deg, #ff9a9e, #fecfef);'></div></div>", unsafe_allow_html=True)
            
            st.markdown("<hr style='border-color:#2d303e;'>", unsafe_allow_html=True)
            
            metrics = [
                ("Moy. Buts / Match", str(stats_h['xg']), str(stats_a['xg'])), 
                ("Série en cours", format_form(stats_h['form_str']), format_form(stats_a['form_str']))
            ]
            for label, v1, v2 in metrics:
                st.markdown(f"""
                    <div style='display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #1a1c23;'>
                        <span style='color:#00ff88; font-weight:bold; font-size:15px;'>{v1}</span>
                        <span style='color:#8892b0; font-size:12px;'>{label.upper()}</span>
                        <span style='color:#60efff; font-weight:bold; font-size:15px;'>{v2}</span>
                    </div>
                """, unsafe_allow_html=True)

# --- VUE 3 : PROFIL D'ÉQUIPE ---
elif st.session_state.view == 'team_profile':
    t = st.session_state.team_data
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        st.markdown("<div class='btn-back'>", unsafe_allow_html=True)
        if st.button("🔙 RETOUR AU MATCH"):
            st.session_state.view = 'match'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
        <div style='text-align:center; padding:30px; margin-bottom:20px;'>
            <img src="{t['logo']}" width="100">
            <h1 style='margin-top:15px; color:white;'>{t['name'].upper()}</h1>
        </div>
    """, unsafe_allow_html=True)

    col_rad, col_stat = st.columns(2)
    
    with col_rad:
        fig = go.Figure(go.Scatterpolar(
            r=[t['stats']['atk'], t['stats']['def'], t['stats']['dyn'], 50, t['stats']['atk']], 
            theta=['Attaque','Défense','Forme Globale','Structure','Attaque'], fill='toself', line_color='#00ff88', name=t['name']
        ))
        fig.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_stat:
        st.markdown("<br>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.markdown(f"""
                <div class='team-stats-box'>
                    <div class='stat-number'>{t['stats']['xg']}</div>
                    <div style='color:#8892b0; font-size:12px; margin-top:5px;'>MOY. BUTS / MATCH</div>
                </div>
            """, unsafe_allow_html=True)
        with col_b2:
            st.markdown(f"""
                <div class='team-stats-box'>
                    <div class='stat-number' style='font-size:18px; line-height:35px;'>{format_form(t['stats']['form_str'])}</div>
                    <div style='color:#8892b0; font-size:12px; margin-top:5px;'>SÉRIE EN COURS</div>
                </div>
            """, unsafe_allow_html=True)

        est_tag = " <span style='font-size:10px; color:#8892b0;'>(Estimé)</span>" if t['stats'].get('is_fallback') else ""

        st.markdown(f"""
            <div style='padding:15px 0; border-bottom:1px solid #1a1c23;'>
                <span style='color:#8892b0;'>Position au Classement</span>
                <span style='color:#00ff88; font-weight:bold; float:right;'>{t['stats']['rank']}</span>
            </div>
            <div style='padding:15px 0; border-bottom:1px solid #1a1c23;'>
                <span style='color:#8892b0;'>Indice Offensif {est_tag}</span>
                <span style='color:#00ff88; font-weight:bold; float:right;'>{t['stats']['atk']} / 100</span>
            </div>
            <div style='padding:15px 0; border-bottom:1px solid #1a1c23;'>
                <span style='color:#8892b0;'>Indice Défensif {est_tag}</span>
                <span style='color:#00ff88; font-weight:bold; float:right;'>{t['stats']['def']} / 100</span>
            </div>
            <div style='padding:15px 0;'>
                <span style='color:#8892b0;'>Dynamique (Forme) {est_tag}</span>
                <span style='color:#00ff88; font-weight:bold; float:right;'>{t['stats']['dyn']} / 100</span>
            </div>
        """, unsafe_allow_html=True)
