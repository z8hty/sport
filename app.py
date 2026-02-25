import os
import streamlit as st
from openai import OpenAI

# 1. Configuration de la page (Mode large et titre propre)
st.set_page_config(page_title="Analyse Sportive Pro", layout="wide")

# 2. Connexion à Groq
client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

# 3. Base de données des équipes avec logos (en PNG pour affichage propre)
# Plus tard, l'API sportive fournira ça automatiquement.
TEAMS = {
    "Real Madrid": "https://upload.wikimedia.org/wikipedia/fr/thumb/c/c7/Logo_Real_Madrid.svg/256px-Logo_Real_Madrid.svg.png",
    "Real Sociedad": "https://upload.wikimedia.org/wikipedia/fr/thumb/f/f1/Logo_Real_Sociedad.svg/256px-Logo_Real_Sociedad.svg.png",
    "Manchester City": "https://upload.wikimedia.org/wikipedia/fr/thumb/b/ba/Badge_Manchester_City_FC_2016.svg/256px-Badge_Manchester_City_FC_2016.svg.png",
    "Olympique de Marseille": "https://upload.wikimedia.org/wikipedia/fr/thumb/4/43/Logo_Olympique_de_Marseille.svg/256px-Logo_Olympique_de_Marseille.svg.png",
    "Paris Saint-Germain": "https://upload.wikimedia.org/wikipedia/fr/thumb/8/86/Paris_Saint-Germain_Logo.svg/256px-Paris_Saint-Germain_Logo.svg.png",
    "Arsenal": "https://upload.wikimedia.org/wikipedia/fr/thumb/5/53/Arsenal_FC_2002_logo.svg/256px-Arsenal_FC_2002_logo.svg.png"
}

def get_match_data(home, away):
    """Simule les données récupérées d'une API sportive"""
    return {
        "match": f"{home} vs {away}",
        "home_team": home,
        "away_team": away,
        "context": {
            "home_form": "V-V-N-V-D",
            "away_form": "V-V-V-V-V",
            "home_xG": 1.8,
            "away_xG": 2.4,
            "home_absentees": "Courtois, Militao",
            "away_absentees": "Aucun",
            "schedule": f"{home} joue l'Europe dans 3 jours."
        },
        "odds": {
            "home_win": 2.80,
            "draw": 3.40,
            "away_win": 2.40,
            "btts": 1.55
        }
    }

def generate_expert_analysis(match_data):
    """Génère le texte d'analyse via l'IA de Groq"""
    prompt = f"""
    Agis comme un expert en analyse de données sportives. Rédige une analyse stricte, logique et mathématique pour {match_data['match']}.
    
    Stats Domicile : Forme {match_data['context']['home_form']}, xG {match_data['context']['home_xG']}, Absents : {match_data['context']['home_absentees']}.
    Stats Extérieur : Forme {match_data['context']['away_form']}, xG {match_data['context']['away_xG']}, Absents : {match_data['context']['away_absentees']}.
    Contexte : {match_data['context']['schedule']}
    
    Directives :
    - 3 paragraphes maximum.
    - Sois factuel. Pas de phrases d'introduction.
    - Analyse la dynamique des xG et l'impact des absents.
    - Conclus sur la meilleure approche de pari.
    """

    # Utilisation du nouveau modèle Llama 3.3 valide sur Groq
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[
            {"role": "system", "content": "Tu es un data-analyste sportif."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

# --- INTERFACE UTILISATEUR (UI) ---

st.title("Moteur d'Analyse Sportive")
st.markdown("Recherchez un match pour obtenir les statistiques profondes et l'analyse prédictive.")

# Zone de recherche avec autocomplétion
col1, col2 = st.columns(2)
with col1:
    home_selection = st.selectbox("Équipe à Domicile", options=list(TEAMS.keys()), index=0)
with col2:
    away_selection = st.selectbox("Équipe à l'Extérieur", options=list(TEAMS.keys()), index=2)

st.write("") # Espace

if st.button("Lancer l'Analyse de ce Match", use_container_width=True):
    data = get_match_data(home_selection, away_selection)
    
    st.divider() # Ligne de séparation propre
    
    # 1. EN-TÊTE DU MATCH (Logos et Noms)
    col_logo1, col_vs, col_logo2 = st.columns([2, 1, 2])
    with col_logo1:
        st.image(TEAMS[home_selection], width=80)
        st.subheader(home_selection)
    with col_vs:
        st.markdown("<h2 style='text-align: center; margin-top: 20px;'>VS</h2>", unsafe_allow_html=True)
    with col_logo2:
        st.image(TEAMS[away_selection], width=80)
        st.subheader(away_selection)

    # 2. PANNEAU DES STATISTIQUES
    st.markdown("### Statistiques Clés")
    stat1, stat2, stat3, stat4 = st.columns(4)
    stat1.metric(label=f"Forme {home_selection}", value=data['context']['home_form'])
    stat2.metric(label=f"xG Moyen {home_selection}", value=data['context']['home_xG'])
    stat3.metric(label=f"Forme {away_selection}", value=data['context']['away_form'])
    stat4.metric(label=f"xG Moyen {away_selection}", value=data['context']['away_xG'])
    
    st.info(f"**Absences majeures :** {home_selection} ({data['context']['home_absentees']}) | {away_selection} ({data['context']['away_absentees']})")

    # 3. GÉNÉRATION DE L'ANALYSE IA
    st.markdown("### Analyse Prédictive")
    with st.spinner("Analyse des données en cours..."):
        analysis = generate_expert_analysis(data)
        st.write(analysis)
        
    # 4. RECOMMANDATIONS DE PARIS
    st.markdown("### Recommandations de Valeur")
    rec1, rec2, rec3 = st.columns(3)
    rec1.success(f"**Safe**\n\nPlus de 1.5 buts (Cote: 1.25)")
    rec2.warning(f"**Modéré**\n\nLes 2 équipes marquent (Cote: {data['odds']['btts']})")
    rec3.error(f"**Agressif**\n\nVictoire de {away_selection} (Cote: {data['odds']['away_win']})")
