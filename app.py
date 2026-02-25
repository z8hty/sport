import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from groq import Groq

# --- 1. CONFIGURATION & DESIGN ---
st.set_page_config(page_title="PredicTech | Terminal Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a; color: #e0e0e0; }
    .main-title { 
        font-size: 50px; font-weight: 900; text-align: center; margin-bottom: 5px;
        background: linear-gradient(90deg, #00ff88, #60efff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .sub-title { text-align: center; color: #8892b0; font-size: 18px; margin-bottom: 40px; }
    .match-container {
        background: #11141b; border: 1px solid #2d303e; border-radius: 12px;
        padding: 20px; transition: 0.3s; height: 280px;
        display: flex; flex-direction: column; justify-content: space-between;
    }
    .match-container:hover { border-color: #00ff88; transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,255,136,0.1); }
    .league-badge { font-size: 10px; color: #00ff88; text-transform: uppercase; font-weight: bold; letter-spacing: 1px; }
    .vs-text { font-size: 20px; font-weight: 900; color: #333; }
    .date-text { font-size: 13px; color: #8892b0; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIQUE API & FONCTIONS ---
API_KEY = st.secrets["RAPIDAPI_KEY"]
GROQ_KEY = st.secrets["GROQ_API_KEY"]
HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

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

def fetch_odds(fixture_id):
    url = "https://api-football-v1.p.rapidapi.com/v3/odds"
    try:
        r = requests.get(url, headers=HEADERS, params={"fixture": fixture_id}).json()
        if r['response']:
            bookmaker = r['response'][0]['bookmakers'][0]
            bets = bookmaker['bets'][0]['values']
            return {bet['value']: bet['odd'] for bet in bets}
    except: pass
    return {"Home": "2.10", "Draw": "3.40", "Away": "3.10"}

def get_ai_prediction(home_team, away_team, context_data):
    client = Groq(api_key=GROQ_KEY)
    prompt = f"Expert Betting. Analyse {home_team} vs {away_team}. Data: {context_data}. Rapport sec: Tactique (2 phrases), Piège, Prono (Safe vs Risqué)."
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return completion.choices[0].message.content

def calculate_metrics(df):
    if df.empty: return 0, 0, 0
    total_mises = df['Mise'].sum()
    total_gains = df['Gain_Potentiel'].sum()
    roi = (total_gains / total_mises) * 100 if total_mises > 0 else 0
    profit_net = total_gains - total_mises
    return total_mises, profit_net, roi

# --- 3. INTERFACE DE RECHERCHE ---
st.markdown("<div class='main-title'>PREDICTECH PRO</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Terminal d'analyse footballistique & gestion de bankroll</div>", unsafe_allow_html=True)

col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
with col_s2:
    search_input = st.text_input("", placeholder="🔍 Chercher une équipe (ex: Real Madrid, Lyon...)", label_visibility="collapsed")

if search_input:
    teams = fetch_teams(search_input)
    if not teams: st.error("❌ Aucune équipe trouvée.")
    else:
        st.markdown(f"### ⚽ Résultats pour : '{search_input}'")
        cols_teams = st.columns(len(teams[:4]))
        for i, res in enumerate(teams[:4]):
            team = res['team']
            with cols_teams[i]:
                st.image(team['logo'], width=70)
                st.write(f"**{team['name']}**")
                if st.button(f"Choisir", key=f"sel_{team['id']}"):
                    st.session_state['selected_id'] = team['id']
                    st.session_state['selected_name'] = team['name']

# --- 4. CALENDRIER & SELECTION MATCH ---
if 'selected_id' in st.session_state:
    st.markdown("---")
    st.markdown(f"## 🗓️ Calendrier : {st.session_state['selected_name']}")
    fixtures = fetch_fixtures(st.session_state['selected_id'])
    if not fixtures: st.info("Aucun match trouvé.")
    else:
        cols_fix = st.columns(3)
        for i, f in enumerate(fixtures):
            with cols_fix[i]:
                date_obj = datetime.fromisoformat(f['fixture']['date'].replace('Z', '+00:00'))
                st.markdown(f"""
                    <div class="match-container">
                        <div class="league-badge">{f['league']['name']}</div>
                        <div style="display:flex; justify-content:space-around; align-items:center;">
                            <img src="{f['teams']['home']['logo']}" width="45">
                            <span class="vs-text">VS</span>
                            <img src="{f['teams']['away']['logo']}" width="45">
                        </div>
                        <div style="text-align:center;">
                            <b>{f['teams']['home']['name']} - {f['teams']['away']['name']}</b><br>
                            <span class="date-text">📅 {date_obj.strftime('%d/%m/%Y - %H:%M')}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"⚡ ANALYSER", key=f"btn_{f['fixture']['id']}", use_container_width=True):
                    st.session_state['current_fixture'] = f

# --- 5. DASHBOARD D'ANALYSE ---
if 'current_fixture' in st.session_state:
    f = st.session_state['current_fixture']
    home_n, away_n = f['teams']['home']['name'], f['teams']['away']['name']

    st.markdown(f"""<div style="background: linear-gradient(90deg, #11141b, #1a1c23); padding: 20px; border-radius: 15px; border: 1px solid #00ff88; margin-top: 30px; text-align: center;">
        <h2 style="color: white; margin:0;">{home_n.upper()} vs {away_n.upper()}</h2>
    </div>""", unsafe_allow_html=True)

    t_stats, t_lineups, t_ai, t_odds, t_vault = st.tabs(["📊 STATS", "📋 COMPOS", "🧠 IA", "💰 VALUE", "🔐 VAULT"])

    with t_stats:
        c_radar, c_metrics = st.columns(2)
        with c_radar:
            cat = ['Attaque', 'Défense', 'Possession', 'Physique', 'Transition', 'Discipline']
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=[85, 70, 90, 80, 75, 95], theta=cat, fill='toself', name=home_n, line_color='#00ff88'))
            fig.add_trace(go.Scatterpolar(r=[75, 85, 80, 70, 85, 75], theta=cat, fill='toself', name=away_n, line_color='#60efff'))
            fig.update_layout(polar=dict(radialaxis=dict(visible=False)), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        with c_metrics:
            for label, v1, v2 in [("Buts/Match", "2.4", "1.8"), ("xG", "2.15", "1.64"), ("Clean Sheets", "12", "8")]:
                st.markdown(f"<div style='display:flex; justify-content:space-between; padding:10px; border-bottom:1px solid #2d303e;'><span style='color:#00ff88;'>{v1}</span><span style='color:#8892b0;'>{label}</span><span style='color:#60efff;'>{v2}</span></div>", unsafe_allow_html=True)

    with t_lineups:
        cl1, cl2 = st.columns(2)
        cl1.markdown(f"**🏠 {home_n}**: Courtois, Rudiger, Bellingham, Mbappé... <br><span style='color:red;'>🚑 Alaba</span>", unsafe_allow_html=True)
        cl2.markdown(f"**✈️ {away_n}**: Ederson, Dias, Rodri, Haaland... <br><span style='color:red;'>🚑 Bobb</span>", unsafe_allow_html=True)

    with t_ai:
        if st.button("🚀 GÉNÉRER L'ANALYSE IA"):
            with st.spinner("Analyse en cours..."):
                ctx = "Home: 2.4 g/m. Away: Strong defense. Last 5 H2H: 3W, 2D."
                res = get_ai_prediction(home_n, away_n, ctx)
                st.markdown(f"<div style='background:#11141b; padding:20px; border-left:5px solid #00ff88;'>{res}</div>", unsafe_allow_html=True)

    with t_odds:
        odds = fetch_odds(f['fixture']['id'])
        m_home = float(odds.get('Home', 2.1))
        st.metric("Cote Bookmaker", m_home, delta="Value Detected" if m_home > 1.9 else "")
        st.line_chart(pd.DataFrame({'Cote': [2.25, 2.15, m_home]}, index=['-24h', '-6h', 'Now']))

    with t_vault:
        with st.expander("📝 Archivage"):
            c1, c2 = st.columns(2)
            u_mise = c1.number_input("Mise (€)", value=10.0)
            u_cote = c2.number_input("Cote", value=m_home)
            if st.button("💾 Sauvegarder"):
                entry = {"Date": datetime.now().strftime("%d/%m"), "Match": f"{home_n}-{away_n}", "Mise": u_mise, "Gain_Potentiel": u_mise*u_cote}
                if 'vault_db' not in st.session_state: st.session_state['vault_db'] = pd.DataFrame(columns=entry.keys())
                st.session_state['vault_db'] = pd.concat([st.session_state['vault_db'], pd.DataFrame([entry])], ignore_index=True)
        
        if 'vault_db' in st.session_state:
            df_v = st.session_state['vault_db']
            m, p, r = calculate_metrics(df_v)
            st.write(f"ROI: **{r:.1f}%** | Profit: **{p:.2f} €**")
            st.dataframe(df_v, use_container_width=True)

    if st.button("🔄 RESET"):
        st.session_state.clear()
        st.rerun()
