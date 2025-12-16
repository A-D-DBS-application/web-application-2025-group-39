# app/utils/outliers.py

def calculate_median(data):
    """Berekent de mediaan (Q2) van een gesorteerde lijst."""
    n = len(data)
    if n % 2 == 1:
        return data[n // 2]
    else:
        return (data[n // 2 - 1] + data[n // 2]) / 2

def detect_vectr_outliers_and_tag(features):
    """
    Detects outliers on the 'vectr_score' (stored as attribute after calculation)
    using the manual IQR method.
    """
    if not features or len(features) < 4:
        for feature in features:
            feature.is_outlier = False
        return features
        
    scores = []
    for feature_item in features:
        score = getattr(feature_item, 'vectr_score', 0.0)
        scores.append(score)
        
    sorted_scores = sorted(scores)
    n = len(sorted_scores)

    # --- 1: Correcte slicing voor de onderste helft ---
    # lower_half pakt altijd de eerste helft
    lower_half = sorted_scores[:n // 2]
    
    # --- 2: Correcte slicing voor de bovenste helft ---
    # Dit zorgt ervoor dat we altijd een list slice terugkrijgen
    # We starten de slice bij de index direct na de onderste helft
    start_of_upper_half_index = n // 2 + (n % 2)
    upper_half = sorted_scores[start_of_upper_half_index:] 
    
    # Nu zijn lower_half en upper_half gegarandeerd lijsten (lists)
    Q1 = calculate_median(lower_half) 
    Q3 = calculate_median(upper_half)
    
    IQR = Q3 - Q1
    
    # Standard IQR bounds
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    for feature_item in features:
        score = getattr(feature_item, 'vectr_score', 0.0)
        feature_item.is_outlier = False
        feature_item.outlier_type = ""
        feature_item.outlier_id = f"outlier-{feature_item.id_feature}" 

        if score < lower_bound:
            feature_item.is_outlier = True
            feature_item.outlier_type = "Low"
        elif score > upper_bound:
            feature_item.is_outlier = True
            feature_item.outlier_type = "High"

    return features