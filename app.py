import os
import openai
import json

# Configuration de la clé API (à mettre dans un fichier .env en production)
openai.api_key = "TA_CLE_API_OPENAI"

def get_match_data(team_home, team_away):
    """
    Ici, tu connecteras plus tard l'API de Sportmonks ou API-Football.
    Pour l'instant, on structure les données exactes dont l'IA a besoin.
    """
    # Données simulées ultra-complètes pour le match
    return {
        "match": f"{team_home} vs {team_away}",
        "competition": "Ligue des Champions",
        "context": {
            "home_form_last_5": "V V N V D", # V=Victoire, N=Nul, D=Défaite
            "away_form_last_5": "V V V V V",
            "home_xG_trend": 1.8, # Expected Goals moyens récents
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
            "btts": 1.55 # Both Teams To Score (Les deux marquent)
        }
    }

def calculate_bet_tiers(match_data):
    """
    Algorithme qui définit les 3 paliers de risque selon les cotes et les stats.
    """
    odds = match_data["odds"]
    
    # Logique simplifiée pour l'exemple : on cherche la valeur
    safe_bet = "Plus de 1.5 buts" # Souvent couvert dans les gros matchs
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
    """
    Le prompt système ultra-strict pour obliger l'IA à faire une vraie analyse logique.
    """
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

    response = openai.chat.completions.create(
        model="gpt-4o", # Le modèle le plus performant pour le raisonnement logique
        messages=[
            {"role": "system", "content": "Tu es un data-analyste sportif de très haut niveau."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3 # Température basse = réponses factuelles et logiques, peu d'improvisation
    )
    
    return response.choices[0].message.content

def main():
    # 1. On cible le match
    home = "Real Madrid"
    away = "Manchester City"
    
    # 2. On récupère les données
    print(f"--- Extraction des données pour {home} vs {away} ---")
    data = get_match_data(home, away)
    
    # 3. On calcule les paliers de paris
    tiers = calculate_bet_tiers(data)
    
    # 4. On génère l'analyse finale via IA
    print("--- Génération de l'analyse IA en cours... ---\n")
    analysis = generate_expert_analysis(data, tiers)
    
    # Affichage du résultat final (ce qui sera envoyé sur ton site/Telegram)
    print(f"⚽ {home} vs {away}")
    print("-" * 30)
    print("🎯 RECOMMANDATIONS :")
    for level, info in tiers.items():
        print(f"[{level}] {info['prono']} (Cote: {info['cote']})")
    print("-" * 30)
    print("🧠 ANALYSE DU MATCH :")
    print(analysis)

if __name__ == "__main__":
    main()
