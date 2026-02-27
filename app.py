import streamlit as st
import requests
import hashlib
import random
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
    .value-badge { background: rgba(0, 255, 136, 0.1); color: #00ff88; border: 1px solid #00ff88; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: bold; display: inline-block; margin-top: 10px;}
    .h2h-box { background: #1a1c23; padding: 10px; border-radius: 8px; font-size: 13px; text-align: center; margin-bottom: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- OUTILS DE FORMATAGE ---
def format_form(form_string):
    if not form_string or form_string == 'Non dispo': return "N/A"
    form_string = form_string[-5:]
    return form_string.replace('W', '🟢').replace('D', '⚪').replace('L', '🔴')

# --- MOTEUR CATALOGUE (0 BLOCAGE) ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_daily_catalog(date_str):
    try:
        r = requests.get(f"{BASE_URL}/fixtures", headers=HEADERS, params={"date": date_str, "timezone": "Europe/Paris"}, timeout=10).json()
        fixtures = r.get('response', [])
        valid_statuses = ['NS', 'TBD', 'PST']
        filtered = [f for f in fixtures if f['league']['id'] in TOP_LEAGUES.keys() and f['fixture']['status']['short'] in valid_statuses]
        filtered.sort(key=lambda x: x['fixture']['timestamp'])
        return filtered
    except:
        return []

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

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_h2h(team_id_1, team_id_2):
    """Récupère l'historique des 3 dernières confrontations"""
    try:
        r = requests.get(f"{BASE_URL}/fixtures/headtohead", headers=HEADERS, params={"h2h": f"{team_id_1}-{team_id_2}", "last": 3}, timeout=5).json()
        return r.get('response', [])
    except: return []

# --- CALCUL DES STATS MATHÉMATIQUES ---
def get_fallback_stats(team_name):
    seed = int(hashlib.md5(team_name.encode()).hexdigest(), 16)
    random.seed(seed)
    if team_name in ["Real Madrid", "Manchester City", "Bayern Munich", "Liverpool", "Arsenal"]: atk, df = 90, 85
    elif team_name in ["Paris Saint Germain", "Barcelona", "Inter", "Bayer Leverkusen", "Juventus"]: atk, df = 85, 82
    elif team_name in ["AC Milan", "Tottenham", "Chelsea", "Manchester United", "Borussia Dortmund"]: atk, df = 81, 78
    elif team_name in ["Marseille", "Lille", "Monaco", "Newcastle", "AS Roma", "Benfica"]: atk, df = 77, 75
    else: atk, df = 73, 72

    return {'atk': atk + random.randint(-2, 2), 'def': df + random.randint(-2, 2), 'dyn': random.randint(65, 85), 'xg': round((atk / 100) * 2.2, 2), 'form_str': 'Non dispo', 'is_fallback': True}

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
            stats['dyn'] = int((sum([3 if r == 'W' else 1 if r == 'D' else 0 for r in form]) / (len(form) * 3)) * 100) if form else 70
            stats['is_fallback'] = False
            return stats
    except: pass
    return get_fallback_stats(team_name)

def calculate_probabilities(stats_h, stats_a):
    power_h = stats_h['atk'] + stats_h['def'] + stats_h['dyn'] + 10 # Avantage domicile
    power_a = stats_a['atk'] + stats_a['def'] + stats_a['dyn']
    if power_h == 0 and power_a == 0: return 33, 34, 33 
    
    diff = power_h - power_a
    prob_h = max(5, min(90, int(45 + (diff * 0.4))))
    prob_a = max(5, min(90, int(30 - (diff * 0.4))))
    return prob_h, 100 - prob_h - prob_a, prob_a

def detect_value_bet(prob_h, prob_n, prob_a, odds, home_name, away_name):
    """Calcul du TRI mathématique : (Probabilité * Cote) > 1.05"""
    value_msg = ""
    try:
        if 'Home' in odds and float(odds['Home']) * (prob_h / 100) > 1.05:
            value_msg = f"🔥 VALUE BET DÉTECTÉE : VICTOIRE {home_name.upper()} (Cote {odds['Home']})"
        elif 'Away' in odds and float(odds['Away']) * (prob_a / 100) > 1.05:
            value_msg = f"🔥 VALUE BET DÉTECTÉE : VICTOIRE {away_name.upper()} (Cote {odds['Away']})"
        elif 'Draw' in odds and float(odds['Draw']) * (prob_n / 100) > 1.10:
            value_msg = f"🔥 VALUE BET DÉTECTÉE : MATCH NUL (Cote {odds['Draw']})"
    except: pass
    return value_msg

def get_ai_prediction(home, away, stats_h, stats_a, odds, value_msg, h2h_data):
    client = Groq(api_key=GROQ_KEY)
    
    h2h_text = "Historique récent : " + ", ".join([f"{f['teams']['home']['name']} {f['goals']['home']}-{f['goals']['away']} {f['teams']['away']['name']}" for f in h2h_data]) if h2h_data else "Pas d'historique récent disponible."

    prompt = f"""Tu es un algorithme de prédiction mathématique de paris sportifs professionnel.
    Analyse ce match : {home} vs {away}.
    
    DATA PURE :
    - {home} (Dom) : Attaque {stats_h['atk']}/100, Défense {stats_h['def']}/100, Forme {stats_h['dyn']}/100, Buts {stats_h['xg']}.
    - {away} (Ext) : Attaque {stats_a['atk']}/100, Défense {stats_a['def']}/100, Forme {stats_a['dyn']}/100, Buts {stats_a['xg']}.
    {h2h_text}
    
    COTES ET VALUE :
    - Cotes 1X2 : 1 ({odds.get('Home', '-')}) | X ({odds.get('Draw', '-')}) | 2 ({odds.get('Away', '-')})
    - Indication Mathématique : {value_msg if value_msg else "Aucune Value Bet franche détectée sur les vainqueurs."}
    
    CONSIGNES STRICTES :
    1. Base-toi UNIQUEMENT sur ces mathématiques et l'historique pour justifier tes choix.
    2. Sois direct, factuel et précis. Ne fais pas d'introduction bavarde.

    DONNE EXACTEMENT 3 CHOIX DE PARIS CLAIRS :
    1. 🟢 PARI SAFE (Sécurité maximale) : Double Chance (ex: 1N), Over/Under buts, ou pari type 'L'une des équipes marque'. Explique mathématiquement.
    2. 🟡 PARI AUDACIEUX (Logique mais mieux coté) : Pari combiné (ex: Victoire + les deux marquent), ou équipe gagne une mi-temps. Justifie-le avec la différence de stats.
    3. 🔴 COUP DE POKER (Le ticket fun) : Score exact très précis ou un écart de but, basé sur la moyenne des buts (xG) et l'historique H2H.
    """
    chat = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}], temperature=0.3)
    return chat.choices[0].message.content

# --- INTERFACE DE GRILLE ---
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
                if show_date:
                    time_str = datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%d/%m - %H:%M')
                else:
                    time_str = datetime.fromisoformat(f['fixture']['date'].replace('Z','+00:00')).strftime('%H:%M')
                
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

# --- VUE 1 : LE CATALOGUE DES PARIS ---
if st.session_state.view == 'home':
    st.markdown("<h1 class='main-title'>PREDICTECH.OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8892b0; margin-bottom:40px;'>CATALOGUE D'ANALYSES ALGORITHMIQUES</p>", unsafe_allow_html=True)

    date_today = datetime.now()
    date_tmrw = date_today + timedelta(days=1)
    date_after = date_today + timedelta(days=2)

    with st.spinner("Synchronisation des vitrines de matchs..."):
        matches_today = fetch_daily_catalog(date_today.strftime("%Y-%m-%d"))
        matches_tmrw = fetch_daily_catalog(date_tmrw.strftime("%Y-%m-%d"))
        matches_after = fetch_daily_catalog(date_after.strftime("%Y-%m-%d"))

    upcoming_matches = matches_tmrw + matches_after

    t1, t2 = st.tabs(["🔥 GROSSES AFFICHES (À VENIR)", "📅 MATCHS DU JOUR"])

    with t1:
        st.markdown("<p style='color:#8892b0; margin-bottom:20px;'>Les chocs majeurs programmés pour demain et les jours suivants.</p>", unsafe_allow_html=True)
        render_match_grid(upcoming_matches, show_date=True)
        
    with t2:
        st.markdown("<p style='color:#8892b0; margin-bottom:20px;'>Toutes les rencontres importantes de la journée.</p>", unsafe_allow_html=True)
        render_match_grid(matches_today, show_date=False)

# --- VUE 2 : ANALYSE DU MATCH ---
elif st.session_state.view == 'match':
    m = st.session_state.match_data
    h, a = m['teams']['home']['name'], m['teams']['away']['name']
    h_id, a_id = m['teams']['home']['id'], m['teams']['away']['id']
    fix_id = m['fixture']['id']
    league_id = m['league']['id']
    
    col_btn, _ = st.columns([1, 5])
    with col_btn:
        st.markdown("<div class='btn-back'>", unsafe_allow_html=True)
        if st.button("🔙 RETOUR CATALOGUE"):
            st.session_state.view = 'home'
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with st.spinner("Extraction des mathématiques et historiques..."):
        standings = fetch_standings(league_id)
        stats_h = calculate_true_stats(h_id, h, standings)
        stats_a = calculate_true_stats(a_id, a, standings)
        prob_h, prob_n, prob_a = calculate_probabilities(stats_h, stats_a)
        odds = get_match_odds(fix_id)
        h2h = fetch_h2h(h_id, a_id)
        
        value_alert = detect_value_bet(prob_h, prob_n, prob_a, odds, h, a)
        
        # Gestion des badges d'estimation
        est_badge = " <span style='font-size:12px; color:#8892b0; font-weight:normal;'>(Stats Estimées)</span>" if stats_h.get('is_fallback') else ""

    st.markdown(f"""
        <div style='text-align:center; padding:30px; border-bottom:1px solid #2d303e; margin-bottom:20px;'>
            <img src="{m['teams']['home']['logo']}" width="60" style="vertical-align:middle; margin-right:20px;">
            <span style='font-size:35px; font-weight:900; color:white; vertical-align:middle;'>{h} vs {a}</span>
            <img src="{m['teams']['away']['logo']}" width="60" style="vertical-align:middle; margin-left:20px;">
            <p style='color:#00ff88; margin-top:10px; font-size:14px;'>COTES 1X2 : 1 ({odds.get('Home', '-')}) | X ({odds.get('Draw', '-')}) | 2 ({odds.get('Away', '-')})</p>
            {f"<div class='value-badge'>{value_alert}</div>" if value_alert else ""}
        </div>
    """, unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button(f"🔍 VOIR LE PROFIL DE {h.upper()}", key="btn_team1"):
            st.session_state.team_data = {'id': h_id, 'name': h, 'logo': m['teams']['home']['logo'], 'stats': stats_h}
            st.session_state.view = 'team_profile'
            st.rerun()
    with col_t2:
        if st.button(f"🔍 VOIR LE PROFIL DE {a.upper()}", key="btn_team2"):
            st.session_state.team_data = {'id': a_id, 'name': a, 'logo': m['teams']['away']['logo'], 'stats': stats_a}
            st.session_state.view = 'team_profile'
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)

    t1, t2 = st.tabs(["🧠 L'ORACLE (PRONOSTICS)", "📊 DATA MATRICES"])
    
    with t1:
        st.markdown("### MOTEUR DE DÉCISION")
        if st.button("LANCER L'ANALYSE MATHÉMATIQUE", use_container_width=False):
            with st.spinner("Llama-3.3 évalue les risques et crée les scénarios..."):
                prediction = get_ai_prediction(h, a, stats_h, stats_a, odds, value_alert, h2h)
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
                st.markdown("<p style='color:#60efff; font-weight:bold; margin-top:10px;'>HISTORIQUE DES CONFRONTATIONS</p>", unsafe_allow_html=True)
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
                    <div style='color:#8892b0; font-size:12px; margin-top:5px;'>MOY. BUTS PAR MATCH</div>
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
