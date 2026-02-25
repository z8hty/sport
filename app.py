import os
import streamlit as st
from openai import OpenAI
import json

# On configure le client pour qu'il pointe vers l'API gratuite de Groq au lieu d'OpenAI
client = OpenAI(
    api_key=st.secrets["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

def get_match_data(team_home, team_away):
    # ... (Garde exactement la même fonction get_match_data qu'avant) ...
    return {
        "match": f"{team_home} vs {team_away}",
        "competition": "Ligue des Champions",
        "context": {
            "home_form_last_5": "V V N V D",
            "away_form_last_5": "V V V V V",
            "home_xG_trend": 1.8,
            "away_xG_trend": 2.4,
            "home_absentees": ["Courtois (Gardien titulaire)", "Militao (Défenseur central)"],
            "away_absentees": ["Aucun"],
            "schedule_pressure": "Le Real Madrid joue un Clasico dans 3 jours. Manchester City a fait tourner au match précédent."
        },
        "odds": {
            "home_win": 2.80,
            "draw": 3.40,
            "away_win": 2.40,
            "over_2_5": 1.65,
            "btts": 1.55
        }
    }

def calculate_bet_tiers(match_data):
    # ... (Garde exactement la même fonction calculate_bet_tiers qu'avant) ...
    odds = match_data["odds"]
    
    safe_bet = "Plus de 1.5 buts"
    safe_odd = 1.25
    mid_bet = "Les deux équipes marquent (BTTS)"
    mid_odd = odds["btts"]
    aggressive_bet = "Victoire de Manchester City"
    aggressive_odd = odds["away_win"]

    return {
        "Safe": {"prono": safe_bet, "cote": safe_odd},
        "Mid": {"prono": mid_bet, "cote": mid_odd},
        "Agressif": {"prono": aggressive_bet, "cote": aggressive_odd}
    }

def generate_expert_analysis(match_data, bet_tiers):
    prompt = f"""
    Tu es un expert en analyse de données sportives et en paris sur le football.
    Génère une analyse logique, directe et sans phrases d'introduction inutiles pour le match suivant.
    
    DONNÉES DU MATCH :
    - Rencontre : {match_data['match']} ({match_data['competition']})
    - Forme {match_data['match'].split(' vs ')[0]} (Domicile) : {match_data['context']['home_form_last_5']}, xG moyen : {match_data['context']['home_xG_trend']}
    - Forme {match_data['match'].split(' vs ')[1]} (Extérieur) : {match_data['context']['away_form_last_5']}, xG moyen : {match_data['context']['away_xG_trend']}
    - Absences Domicile : {', '.join(match_data['context']['home_absentees'])}
    - Absences Extérieur : {', '.join(match_data['context']['away_absentees'])}
    - Contexte calendrier : {match_data['context']['schedule_pressure']}
    
    RECOMMANDATIONS DE PARIS :
    - SAFE : {bet_tiers['Safe']['prono']} (Cote : {bet_tiers['Safe']['cote']})
    - MID : {bet_tiers['Mid']['prono']} (Cote : {bet_tiers['Mid']['cote']})
    - AGRESSIF : {bet_tiers['Agressif']['prono']} (Cote : {bet_tiers['Agressif']['cote']})

    RÈGLES DE RÉDACTION :
    1. Analyse la dynamique réelle (utilise les xG et les absences pour justifier ton propos).
    2. Prends en compte le calendrier et la fatigue.
    3. Justifie brièvement pourquoi chaque pari (Safe, Mid, Agressif) est pertinent selon les statistiques fournies.
    4. Rédige 3 paragraphes maximum. Sois tranchant, professionnel et mathématique. Aucun blabla générique du type "Le ballon est rond".
    """

    # Ici, on utilise le nouveau 'client' configuré avec Groq
    response = client.chat.completions.create(
        model="llama3-70b-8192", # Le meilleur modèle open-source actuel dispo gratuitement sur Groq
        messages=[
            {"role": "system", "content": "Tu es un data-analyste sportif de très haut niveau."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content

# Pour que ça s'affiche sur la page Streamlit (interface graphique basique)
st.title("⚽ Moteur IA - Pronostics Football")

home = st.text_input("Équipe à Domicile", "Real Madrid")
away = st.text_input("Équipe à l'Extérieur", "Manchester City")

if st.button("Lancer l'Analyse IA"):
    data = get_match_data(home, away)
    tiers = calculate_bet_tiers(data)
    
    with st.spinner("L'IA génère l'analyse complète..."):
        analysis = generate_expert_analysis(data, tiers)
    
    st.subheader("🎯 RECOMMANDATIONS")
    for level, info in tiers.items():
        st.write(f"**[{level}]** {info['prono']} (Cote: {info['cote']})")
        
    st.subheader("🧠 ANALYSE DU MATCH")
    st.write(analysis)
