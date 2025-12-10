# app/utils/knapsack_optimizer.py
import numpy as np

# Aangenomen dat deze functie gedefinieerd wordt in calculations.py of de route
# We moeten deze lokaal repliceren of importeren. Voor nu, definiëren we hem hier 
# met de nodige conversies naar float.
def calculate_feature_cost(feature):
    """Berekent de totale ontwikkelingskosten van een feature (€), met conversie naar float."""
    # Gebruik float() om zeker te zijn van het type
    invest_hours = float(feature.investment_hours) if feature.investment_hours is not None else 0.0
    hourly_rate = float(feature.hourly_rate) if feature.hourly_rate is not None else 0.0
    return invest_hours * hourly_rate

def optimize_roadmap(roadmap, features, alpha=0.5):
    """
    Greedy Optimalisatie d.m.v. Knapzak Heuristiek (2 Constraints: Tijd en Kosten).

    :param roadmap: Roadmap object (Capaciteit)
    :param features: Lijst van Features_ideas objecten (Waarde & Gewicht)
    :param alpha: Strategische wegingsfactor (0.0=Kosten Focus, 1.0=Tijd Focus)
    :return: Een lijst van geselecteerde Features_ideas objecten.
    """

    # 1. Capaciteiten bepalen (C_T en C_C) - ZEKER ZIJN DAT ALLES FLOAT IS
    # Dit voorkomt de TypeError: 'float' and 'decimal.Decimal'
    
    # We optimaliseren over 1 sprint.
    MAX_TIME_CAPACITY = float(roadmap.sprint_capacity) * float(roadmap.team_size)
    MAX_COST_CAPACITY = float(roadmap.budget_allocation)
    
    # Zorg voor een minimale capaciteit om delen door nul te voorkomen in normalisatie
    max_time = MAX_TIME_CAPACITY if MAX_TIME_CAPACITY > 0 else 1.0
    max_cost = MAX_COST_CAPACITY if MAX_COST_CAPACITY > 0 else 1.0


    features_to_optimize = []
    
    # 2. Dichtheid (D_i) berekenen voor elke feature
    for f in features:
        # Cruciale Check: VECTR-score, Uren en Tarief moeten bestaan
        if (f.vectr_score is None or f.investment_hours is None or f.hourly_rate is None or
            f.vectr_score <= 0): # Negeer features met 0 of negatieve ROI/VECTR
            continue
            
        # *** WAARDEN CONVERTEREN NAAR FLOAT VOOR VEILIGE BEREKENING ***
        value = float(f.vectr_score)
        time_weight = float(f.investment_hours)
        cost_weight = calculate_feature_cost(f)
        
        # 2a. Harde filter: Feature mag niet groter zijn dan de totale capaciteit (per constraint)
        if time_weight > MAX_TIME_CAPACITY or cost_weight > MAX_COST_CAPACITY:
            continue

        # 2b. Normalisatie: Schaalt gewichten naar 0-1 (t.o.v. de maximale capaciteit)
        normalized_time_weight = time_weight / max_time
        normalized_cost_weight = cost_weight / max_cost
        
        # 2c. Gecombineerd Gewogen Gewicht (de noemer) - Dit is de foutregel uit de traceback
        # Alpha is al float, nu zijn de gewichten ook float.
        combined_weight = (alpha * normalized_time_weight) + ((1.0 - alpha) * normalized_cost_weight)
        
        # 2d. Dichtheid berekenen
        density = value / combined_weight if combined_weight > 0 else 0.0
            
        features_to_optimize.append({
            'feature': f,
            'density': density,
            'time_weight': time_weight, # Gebruik de float-waarden hier
            'cost_weight': cost_weight,
            'value': value
        })

    # 3. Sorteren: Greedy Choice (op Dichtheid)
    features_to_optimize.sort(key=lambda x: x['density'], reverse=True)
    
    # 4. Selectie: Vul de Knapzak
    selected_features = []
    current_time_used = 0.0 # Gebruik float voor tellers
    current_cost_used = 0.0
    
    for item in features_to_optimize:
        # Check of BEIDE constraints worden gerespecteerd
        if (current_time_used + item['time_weight'] <= MAX_TIME_CAPACITY and 
            current_cost_used + item['cost_weight'] <= MAX_COST_CAPACITY):
            
            # Voeg item toe aan Knapzak
            selected_features.append(item['feature'])
            current_time_used += item['time_weight']
            current_cost_used += item['cost_weight']
            
    return selected_features