# utils/calculations.py (of in je routesbestand)
# Dit bestand bevat hulpprogramma's voor het converteren en berekenen van scores (ROI, TTV, VECTR).

def to_float(val, default=0.0):                                       # Converteert een willekeurige waarde naar een float (decimaal getal).
    try:
        return float(val)                                             # Probeer de waarde om te zetten naar een float
    except (TypeError, ValueError):
        return default                                                # Geef de standaardwaarde (0.0) terug bij fouten

def calc_roi(extra_revenue, churn_reduction, cost_savings,
                     investment_hours, hourly_rate, opex_hours, other_costs): # Bereken de Return on Investment (ROI) in procenten.
    
    # De totale verwachte financiële winst (Gains)
    gains = to_float(extra_revenue) + to_float(churn_reduction) + to_float(cost_savings)
    
    # De ontwikkelingskosten: Uren vermenigvuldigd met het uurtarief
    dev_cost = to_float(investment_hours) * to_float(hourly_rate)
    
    # De totale kosten (Costs)
    costs = dev_cost + to_float(opex_hours) + to_float(other_costs)
    
    if costs > 0:
        # Formule voor ROI: ((Winst - Kosten) / Kosten) * 100, afgerond op 2 decimalen
        return round(((gains - costs) / costs) * 100, 2)
    return None

def calc_ttv(ttm_weeks, ttbv_weeks):                                  # Bereken TTV: TTM + TTBV
    
    total = to_float(ttm_weeks) + to_float(ttbv_weeks)
    
    # Geeft de TTV terug als een geheel getal (int), indien positief
    return int(total) if total > 0 else None


def to_numeric(raw_value):                                            # Converteert een ruwe waarde naar een float, met 0 als fallback.
    if raw_value is None:
        return 0                                                      # Behandel None als 0
    try:
        # Probeer om te zetten naar een float na het verwijderen van witruimte
        return float(str(raw_value).strip())
    except ValueError:
        return 0
    
def calculate_vectr_scores(features_list):                             # Berekent de VECTR-score en voegt deze toe aan elk Feature-object.
    
    # Itereert over elk feature-object in de lijst
    for f in features_list:
        
        # Haal TTV op, gebruik 5.5 als standaardwaarde als deze None is
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        # Haal ROI op, gebruik 0.0 als standaardwaarde
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        # Haal Confidence Score (Quality Score) op, gebruik 0.0 als standaardwaarde
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        
        # De VECTR score is het gewogen product van TTV * ROI * Confidence
        vectr_score = ttv_weeks * roi_percent * confidence_score
        
        # Voeg de afgeronde VECTR-score (op 2 decimalen) toe aan het feature-object
        setattr(f, "vectr_score", round(vectr_score, 2))
        
    return features_list                                              # Retourneer de bijgewerkte lijst