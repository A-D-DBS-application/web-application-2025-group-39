# app/utils/outliers.py

def calculate_median(data):
    """Berekent de mediaan (Q2) van een gesorteerde lijst."""
    n = len(data)
    if not data:
        return 0.0
    if n % 2 == 1:
        return data[n // 2]
    else:
        return (data[n // 2 - 1] + data[n // 2]) / 2

def get_iqr_bounds(features, attribute_name):
    """Berekent de statistische grenzen voor een specifiek attribuut van de features."""
    values = [getattr(f, attribute_name, 0.0) or 0.0 for f in features]
    if len(values) < 4:
        return None, None
        
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    lower_half = sorted_vals[:n // 2]
    start_of_upper_half_index = n // 2 + (n % 2)
    upper_half = sorted_vals[start_of_upper_half_index:] 
    
    Q1 = calculate_median(lower_half) 
    Q3 = calculate_median(upper_half)
    IQR = Q3 - Q1
    
    # Gebruik de standaard 1.5 * IQR regel voor uitschieters
    return (Q1 - 1.5 * IQR), (Q3 + 1.5 * IQR)

def detect_vectr_outliers_and_tag(features):
    """
    Detecteert uitschieters voor VECTR, ROI en TtV.
    """
    if not features:
        return features

    # Reset en initialiseer velden voor alle features
    for f in features:
        f.is_outlier = False
        f.outlier_type = ""
        f.outlier_id = f"outlier-{f.id_feature}"

    # De lijst met metrieken die gecontroleerd moeten worden
    # Hier zit 'ttv_weeks' nu expliciet bij
    metrics = {
        'vectr_score': 'VECTR',
        'roi_percent': 'ROI',
        'ttv_weeks': 'TtV'
    }

    for attr, label in metrics.items():
        low_bound, high_bound = get_iqr_bounds(features, attr)
        
        if low_bound is None: 
            continue # Te weinig data (minimaal 4 nodig)

        for f in features:
            val = getattr(f, attr, 0.0) or 0.0
            
            # Bestaande redenen ophalen om ze te combineren
            reasons = f.outlier_type.split(', ') if f.outlier_type else []

            if val < low_bound:
                reasons.append(f"Low {label}")
                f.is_outlier = True
            elif val > high_bound:
                reasons.append(f"High {label}")
                f.is_outlier = True
            
            # Zet de samengevoegde redenen terug (bijv: "High ROI, High TtV")
            f.outlier_type = ", ".join(reasons)

    return features