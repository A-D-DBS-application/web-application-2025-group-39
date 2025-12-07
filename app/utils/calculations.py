# utils/calculations.py (of in je routesbestand)
def to_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def calc_roi(extra_revenue, churn_reduction, cost_savings,
                     investment_hours, hourly_rate, opex_hours, other_costs):
    gains = to_float(extra_revenue) + to_float(churn_reduction) + to_float(cost_savings)
    dev_cost = to_float(investment_hours) * to_float(hourly_rate)
    costs = dev_cost + to_float(opex_hours) + to_float(other_costs)
    if costs > 0:
        return round(((gains - costs) / costs) * 100, 2)
    return None

def calc_ttv(ttm_weeks, ttbv_weeks):
    total = to_float(ttm_weeks) + to_float(ttbv_weeks)
    return int(total) if total > 0 else None



def to_numeric(raw_value):
    if raw_value is None:
        return 0
    try:
        return float(str(raw_value).strip())
    except ValueError:
        return 0
    
def calculate_vectr_scores(features_list):
    """Berekent de VECTR-score en voegt deze toe aan elk Feature-object."""
    for f in features_list:
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        vectr_score = ttv_weeks * roi_percent * confidence_score
        setattr(f, "vectr_score", round(vectr_score, 2))
    return features_list

