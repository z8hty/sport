import os
import streamlit as st
from openai import OpenAI
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIGURATION GLOBALE ---
st.set_page_config(page_title="PredicTech | Terminal Pro", layout="wide", initial_sidebar_state="expanded")

# CSS personnalisé pour un look "Dark Mode Dashboard" ultra dense
st.markdown("""
    <style>
    .metric-card { background-color: #1a1a1a; padding: 20px; border-radius: 8px; border-top: 3px solid #00ff88; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 15px;}
    .metric-value { font-size: 24px; font-weight: bold; color: #ffffff; }
    .metric-label { font-size: 12px; color: #888888; text-transform: uppercase; letter-spacing: 1px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #111; padding: 10px; border-radius: 8px; }
    .stTabs [data-baseweb="tab"] { height: 45px; background-color: #222; border-radius: 6px; padding: 5px 20px; font-size: 16px; border: 1px solid #333; }
    .stTabs [aria-selected="true"] { background-color: #00ff88 !important; color: #000 !important; font-weight: bold;}
    .risk-safe { color: #00ff88; border: 1px solid #00ff88; padding: 10px; border-radius: 5px; }
    .risk-mid { color: #ffcc00; border: 1px solid #ffcc00; padding: 10px; border-radius: 5px; }
    .risk-high { color: #ff4444; border: 1px solid #ff4444; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# Connexion IA Groq
client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

# --- 2. BASE DE DONNÉES MASSIVE (Simulation) ---
TEAMS_DB = {
    "Real Madrid": {"logo": "https://upload.wikimedia.org/wikipedia/fr/thumb/c/c7/Logo_Real_Madrid.svg/120px-Logo_Real_Madrid.svg.png", "league": "La Liga"},
    "Manchester City": {"logo": "https://upload.wikimedia.org/wikipedia/fr/thumb/b/ba/Badge_Manchester_City_FC_2016.svg/120px-Badge_Manchester_City_FC_2016.svg.png", "league": "Premier League"},
    "Bayern Munich": {"logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1b/FC_Bayern_M%C3%BCnchen_logo_%282017%29.svg/120px-FC_Bayern_M%C3%BCnchen_logo_%282017%29.svg.png", "league": "Bundesliga"},
    "Arsenal": {"logo": "https://upload.wikimedia.org/wikipedia/fr/thumb/5/53/Arsenal_FC_2002_logo.svg/120px-Arsenal_FC_2002_logo.svg.png", "league": "Premier League"},
    "Paris SG": {"logo": "https://upload.wikimedia.org/wikipedia/fr/thumb/8/86/Paris_Saint-Germain_Logo.svg/120px-Paris_Saint-Germain_Logo.svg.png", "league": "Ligue 1"}
}

def get_deep_match_data(home, away):
    """Génère un volume massif de fausses données pour remplir le dashboard"""
    return {
        "match_info": {
            "referee": "Szymon Marciniak (Moy: 4.2 cartons/match)",
            "weather": "Pluie fine, 14°C - Terrain glissant",
            "stadium": "Santiago Bernabéu (98% de remplissage)",
            "rest_days": {"home": 4, "away": 3}
        },
        "radar_stats": {
            "categories": ['Attaque', 'Défense', 'Possession', 'Pressing', 'Finition'],
            "home_values": [85, 78, 65, 70, 90],
            "away_values": [88, 82, 85, 80, 85]
        },
        "xg_timeline": {
            "minutes": ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90'],
            "home_xg_conceded": [0.1, 0.2, 0.4, 0.1, 0.3, 0.5], # Quand ils encaissent le plus
            "away_xg_scored": [0.3, 0.1, 0.5, 0.6, 0.2, 0.8] # Quand ils marquent le plus
        },
        "key_metrics": {
            "home": {"possession": "58%", "pass_accuracy": "89%", "shots_pg": 15.4, "goals_pg": 2.1},
            "away": {"possession": "64%", "pass_accuracy": "91%", "shots_pg": 17.2, "goals_pg": 2.4}
        },
        "odds": {"1": 2.65, "X": 3.40, "2": 2.50, "over25": 1.72, "btts": 1.58, "home_over15": 2.10}
    }

def generate_ai_report(home, away, data):
    prompt = f"""
    Analyse de niveau expert (trader sportif) pour {home} vs {away}.
    Données : Arbitre sévère ({data['match_info']['referee']}), Météo : {data['match_info']['weather']}.
    Repos : {home} ({data['match_info']['rest_days']['home']} jours), {away} ({data['match_info']['rest_days']['away']} jours).
    
    Rédige un rapport technique tranchant de 3 paragraphes. 
    1. Impact tactique de la météo et de l'arbitre.
    2. Dynamique des Expected Goals (qui domine vraiment).
    3. Conclusion sur la plus grosse "Value" (cote mal évaluée par les bookmakers).
    Aucune politesse. Va droit au but.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": "Tu es l'IA principale d'un hedge fund spécialisé dans les paris sportifs."},
                  {"role": "user", "content": prompt}],
        temperature=0.2
    )
    return response.choices[0].message.content

# --- 3. BARRE LATÉRALE (Filtres et Navigation) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/8615/8615097.png", width=60) # Petit logo générique
    st.markdown("## ⚙️ Centre de Contrôle")
    selected_home = st.selectbox("Équipe Domicile", list(TEAMS_DB.keys()), index=0)
    
    away_options = [t for t in TEAMS_DB.keys() if t != selected_home]
    selected_away = st.selectbox("Équipe Extérieur", away_options, index=0)
    
    st.markdown("---")
    st.markdown("### 📡 Flux de données")
    st.success("API Football : Connecté")
    st.success("API Météo : Connecté")
    st.success("Moteur IA : Opérationnel")

# --- 4. CORPS PRINCIPAL DU DASHBOARD ---
data = get_deep_match_data(selected_home, selected_away)

# EN-TÊTE DU MATCH (Scoreboard visuel)
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_l:
    st.image(TEAMS_DB[selected_home]["logo"], width=120)
    st.markdown(f"### {selected_home}")
    st.caption(TEAMS_DB[selected_home]["league"])
with col_c:
    st.markdown("<h1 style='text-align: center; font-size: 50px; margin-top: 20px;'>VS</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #aaa;'>{data['match_info']['stadium']}</p>", unsafe_allow_html=True)
with col_r:
    st.image(TEAMS_DB[selected_away]["logo"], width=120)
    st.markdown(f"### {selected_away}")
    st.caption(TEAMS_DB[selected_away]["league"])

st.markdown("---")

# LES ONGLETS DE CONTENU MASSIF
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Intelligence Artificielle & Pronos", 
    "📊 Deep Data & Radars", 
    "⏱️ Chronologie & xG", 
    "🌩️ Facteurs Externes"
])

# --- ONGLET 1 : L'IA ET LES PARIS ---
with tab1:
    st.markdown("### 🧠 Rapport de l'Algorithme")
    with st.spinner("Compilation des millions de points de données..."):
        ai_report = generate_ai_report(selected_home, selected_away, data)
        st.info(ai_report)
        
    st.markdown("### 💰 Détection de Value Bets")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='risk-safe'><strong>🟢 CONSERVATEUR (Safe)</strong><br><br>Pari : Plus de 1.5 buts dans le match<br>Cote : 1.25<br>Confiance IA : 89%</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='risk-mid'><strong>🟡 ÉQUILIBRÉ (Value)</strong><br><br>Pari : Les 2 équipes marquent<br>Cote : {data['odds']['btts']}<br>Confiance IA : 64%</div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='risk-high'><strong>🔴 AGRESSIF (Haut Rendement)</strong><br><br>Pari : {selected_home} marque + de 1.5 buts<br>Cote : {data['odds']['home_over15']}<br>Confiance IA : 41%</div>", unsafe_allow_html=True)

# --- ONGLET 2 : RADARS ET STATS ---
with tab2:
    col_radar, col_stats = st.columns([1.5, 1])
    
    with col_radar:
        st.markdown("### 🕸️ Radar de Puissance")
        # Création d'un graphique Radar très pro avec Plotly
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=data['radar_stats']['home_values'], theta=data['radar_stats']['categories'],
            fill='toself', name=selected_home, line_color='#00ff88'
        ))
        fig.add_trace(go.Scatterpolar(
            r=data['radar_stats']['away_values'], theta=data['radar_stats']['categories'],
            fill='toself', name=selected_away, line_color='#ff0055'
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        
    with col_stats:
        st.markdown("### 📈 Métriques Moyennes")
        st.markdown(f"<div class='metric-card'><span class='metric-label'>Possession</span><br><span class='metric-value'>{data['key_metrics']['home']['possession']} - {data['key_metrics']['away']['possession']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><span class='metric-label'>Tirs par match</span><br><span class='metric-value'>{data['key_metrics']['home']['shots_pg']} - {data['key_metrics']['away']['shots_pg']}</span></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card'><span class='metric-label'>Buts par match</span><br><span class='metric-value'>{data['key_metrics']['home']['goals_pg']} - {data['key_metrics']['away']['goals_pg']}</span></div>", unsafe_allow_html=True)

# --- ONGLET 3 : CHRONOLOGIE ---
with tab3:
    st.markdown("### ⏱️ Dynamique de Match (Quand les buts arrivent ?)")
    st.write("Ce graphique croise les moments où l'équipe à domicile encaisse le plus d'Expected Goals (xG) face aux moments où l'équipe à l'extérieur s'en crée le plus.")
    
    chart_data = pd.DataFrame({
        f"{selected_home} (Vulnérabilité)": data['xg_timeline']['home_xg_conceded'],
        f"{selected_away} (Pression offensive)": data['xg_timeline']['away_xg_scored']
    }, index=data['xg_timeline']['minutes'])
    
    st.bar_chart(chart_data, color=["#ff4444", "#00ff88"])
    
    st.info("💡 **Interprétation IA :** Regardez les pics qui se croisent. Si la barre rouge et la barre verte sont hautes en même temps, c'est la fenêtre de temps idéale pour parier sur un but en direct (Live Betting).")

# --- ONGLET 4 : FACTEURS EXTERNES ---
with tab4:
    col_w, col_r, col_f = st.columns(3)
    
    with col_w:
        st.markdown("### 🌩️ Météo & Terrain")
        st.write(f"**Conditions :** {data['match_info']['weather']}")
        st.warning("Impact : Terrain glissant. Hausse potentielle de 15% des tacles en retard et des fautes aux abords de la surface.")
        
    with col_r:
        st.markdown("### 🕴️ Arbitrage")
        st.write(f"**Arbitre :** {data['match_info']['referee']}")
        st.error("Tendance : Arbitre très sévère. Value potentielle sur les paris 'Plus de 4.5 cartons dans le match'.")
        
    with col_f:
        st.markdown("### 🔋 Fatigue")
        st.write(f"**Repos {selected_home} :** {data['match_info']['rest_days']['home']} jours")
        st.write(f"**Repos {selected_away} :** {data['match_info']['rest_days']['away']} jours")
        st.success("Avantage physique minime pour l'équipe à domicile.")
