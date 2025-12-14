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

def calc_ttv_scaled(ttm_low_limit, ttm_high_limit, ttbv_low_limit, ttbv_high_limit, ttv_weeks_raw):
    """
    Berekent de geschaalde TTV-score (0-10) op basis van project-specifieke TtV-limieten.
    Lage TTV (weken) resulteert in een hoge TTV_scaled (score).
    """
    # Zorg dat alle inputs floats zijn
    ttm_high_limit = to_float(ttm_high_limit)
    ttm_low_limit = to_float(ttm_low_limit)
    ttbv_high_limit = to_float(ttbv_high_limit)
    ttbv_low_limit = to_float(ttbv_low_limit)
    ttv_weeks_raw = to_float(ttv_weeks_raw) # De onbewerkte TTM + TTBV in weken

    # Bepaal de totale min/max tijd van het project
    TTV_MAX = ttm_high_limit + ttbv_high_limit
    TTV_MIN = ttm_low_limit + ttbv_low_limit

    if TTV_MAX > TTV_MIN:
        # Normaliseer naar [0, 10]: 0 = snel (MIN), 10 = langzaam (MAX)
        ttv_norm_0_10 = (ttv_weeks_raw - TTV_MIN) / (TTV_MAX - TTV_MIN) * 10
        
        # Schaal omgekeerd: 10.0 - TTV zorgt voor omgekeerde schaal (10 is snel, 0 is langzaam)
        ttv_scaled = 10.0 - min(max(ttv_norm_0_10, 0), 10)
    else:
        # Kan niet schalen, zet op neutrale/standaard score
        ttv_scaled = 0.0
    
    return ttv_scaled


def to_numeric(raw_value):                                            # Converteert een ruwe waarde naar een float, met 0 als fallback.
    if raw_value is None:
        return 0                                                      # Behandel None als 0
    try:
        # Probeer om te zetten naar een float na het verwijderen van witruimte
        return float(str(raw_value).strip())
    except ValueError:
        return 0
    
def calculate_vectr_scores(features_list, ttm_limits, ttbv_limits):
    """
    Berekent de VECTR-score en voegt deze toe aan elk Feature-object.
    Gebruikt de geschaalde TTV (0-10) in de berekening.
    
    :param ttm_limits: Tuple (ttm_low_limit, ttm_high_limit).
    :param ttbv_limits: Tuple (ttbv_low_limit, ttbv_high_limit).
    """
    
    # Ontpak de limieten (voor leesbaarheid)
    try:
        ttm_low, ttm_high = ttm_limits
        ttbv_low, ttbv_high = ttbv_limits
    except Exception:
        # Fallback als limieten niet goed zijn doorgegeven
        ttm_low, ttm_high = 0.0, 0.0
        ttbv_low, ttbv_high = 0.0, 0.0


    # Itereert over elk feature-object in de lijst
    for f in features_list:
        
        # 1. Haal TTV in weken op (ruwe TTV)
        ttv_weeks_raw = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        
        # 2. BEREKEN de geschaalde TTV score (0-10)
        ttv_scaled = calc_ttv_scaled(
            ttm_low,
            ttm_high,
            ttbv_low,
            ttbv_high,
            ttv_weeks_raw
        )
        
        # 3. Haal ROI en Confidence Score op
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        
        # De VECTR score is het gewogen product van TTV_SCALED * ROI * Confidence
        # BELANGRIJK: Gebruik nu ttv_scaled i.p.v. ttv_weeks
        vectr_score = ttv_scaled * (roi_percent / 100.0) * confidence_score
        
        # Voeg de afgeronde VECTR-score (op 2 decimalen) toe aan het feature-object
        setattr(f, "vectr_score", round(vectr_score, 2))
        
    return features_list                                   # Retourneer de bijgewerkte lijst



def calculate_feature_cost(feature):
    """
    Berekent de totale ontwikkelingskosten van een feature (€).
    Zorgt voor float conversie van de inputs.
    """
    # Gebruik to_numeric uit dit bestand om float conversie te verzekeren
    dev_cost = to_float(feature.investment_hours) * to_float(feature.hourly_rate)
    
    # De totale kosten (Costs)
    costs = dev_cost + to_float(feature.opex_hours) + to_float(feature.other_costs)
     
    return costs