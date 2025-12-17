# app/utils/knapsack_optimizer.py

def optimize_roadmap(roadmap, features, alpha=0.5):
    
    # Greedy optimalisatie met knapzakheuristiek (2 constraints: tijd en kosten).
    # We gebruiken een fractionele knapzak benadering voor de sorteer-dichtheid,
    # maar een 0/1 selectie (wel of niet nemen) in de daadwerkelijke selectiefase.

    #:param roadmap: Roadmap object met attributen total_time_capacity (in uren), budget_allocation
    #:param features: iterable van feature-objecten met attributen: vectr_score, investment_hours, hourly_rate
    #:param alpha: float in [0,1], weging tussen tijd (1.0) en kosten (0.0)
    #:return: lijst van geselecteerde feature-objecten
    
    # 1) Capaciteiten bepalen en veilig stellen als float

    try:
        total_time_capacity = float(roadmap.time_capacity)
    except Exception:
        # Fallback naar 0.0 als de waarde ontbreekt of ongeldig is
        total_time_capacity = 0.0
    
    # Oorspronkelijke budgetallocatie blijft
    try:
        budget_allocation = float(roadmap.budget_allocation)
    except Exception:
        budget_allocation = 0.0

    # Definieer de maximale capaciteiten.
    # MAX_TIME_CAPACITY is nu direct de totale beschikbare tijd in uren.
    MAX_TIME_CAPACITY = total_time_capacity
    MAX_COST_CAPACITY = budget_allocation

    # Voorkom deling door nul bij normalisatie
    # Zorgt ervoor dat we kunnen normaliseren naar [0, 1] zelfs als de capaciteit 0 is.
    max_time = MAX_TIME_CAPACITY if MAX_TIME_CAPACITY > 0.0 else 1.0
    max_cost = MAX_COST_CAPACITY if MAX_COST_CAPACITY > 0.0 else 1.0

    features_to_optimize = []  # lijst van dicts met keys: feature, density, time_weight, cost_weight, value

    # 2) Bereken dichtheid (density) voor iedere feature en filter ongeschikte features weg
    for f in features:
        # Validatie en conversie van benodigde velden
        # We controleren of de feature de benodigde attributen heeft om de waarde en kosten te berekenen.
        
        if getattr(f, 'vectr_score', None) is None:
            # Geen score -> negeren. VECTR score is onze 'value' in de knapzak.
            continue
        if getattr(f, 'investment_hours', None) is None:
            # Tijdsinvestering is het 'gewicht' voor de tijds-constraint.
            continue
        if getattr(f, 'hourly_rate', None) is None:
            # Uurtarief is nodig om de kosten ('gewicht' voor de kosten-constraint) te berekenen.
            continue

        # Zet waarden om naar floats, met fallback op 0.0
        try:
            value = float(f.vectr_score)
        except Exception:
            # Ongeldig of niet-numeriek VECTR -> overslaan
            continue

        # Negeer features zonder positieve waarde (we zoeken naar features die waarde toevoegen)
        if value <= 0.0:
            continue

        try:
            time_weight = float(f.investment_hours)
        except Exception:
            time_weight = 0.0

        try:
            hourly_rate = float(f.hourly_rate)
        except Exception:
            hourly_rate = 0.0

        # Bereken kosten van feature: Tijd * Tarief = Kosten
        # Haal de extra kostenvelden op (met fallback naar 0.0)
        try:
            opex = float(getattr(f, 'opex', 0.0) or 0.0)
            other_costs = float(getattr(f, 'other_costs', 0.0) or 0.0)
        except Exception:
            opex = 0.0
            other_costs = 0.0

        # Bereken de VOLLEDIGE kosten van de feature
        cost_weight = (time_weight * hourly_rate) + opex + other_costs

        # Harde filter: als één van de gewichten groter is dan totale capaciteit -> overslaan
        # Deze feature kan per definitie niet in de roadmap passen.
        if time_weight > MAX_TIME_CAPACITY or cost_weight > MAX_COST_CAPACITY:
            continue

        # Normaliseer gewichten t.o.v. maxima (waardes in [0,1])
        # Dit is essentieel voor het combineren van de twee gewichten (tijd en kosten).
        normalized_time_weight = time_weight / max_time
        normalized_cost_weight = cost_weight / max_cost

        # Haal alpha op en zorg dat het een float is, fallback naar 0.5 indien nodig
        try:
            alpha_val = float(alpha)
        except Exception:
            alpha_val = 0.5

        # Gecombineerd gewicht volgens alpha-weging: 
        # (alpha * Genormaliseerde Tijd) + ((1 - alpha) * Genormaliseerde Kosten)
        combined_weight = (alpha_val * normalized_time_weight) + ((1.0 - alpha_val) * normalized_cost_weight)

        # Bereken de dichtheid: Waarde / Gecombineerd Gewicht
        # Dit bepaalt de prioriteit: Hoge waarde per gewicht is beter.
        if combined_weight > 0.0:
            density = value / combined_weight
        else:
            # Als gewicht 0 is, geven we een 0 dichtheid om deze niet te prioriteren (mag niet voorkomen).
            density = 0.0

        features_to_optimize.append({
            'feature': f,
            'density': density,
            'time_weight': time_weight,
            'cost_weight': cost_weight,
            'value': value
        })

    # 3) Handmatige sortering op density (desc) 
    # De Selection Sort logica is behouden om de oorspronkelijke code te respecteren, 
    # maar in een productieomgeving zou `features_to_optimize.sort(key=lambda x: x['density'], reverse=True)` 
    # efficiënter en leesbaarder zijn.
    n = len(features_to_optimize)
    i = 0
    while i < n - 1:
        # Zoek index van het maximum in de rest van de lijst (i..n-1)
        max_idx = i
        j = i + 1
        while j < n:
            # Veilig de 'density' waarden ophalen en vergelijken.
            d_j = features_to_optimize[j].get('density', 0.0)
            d_max = features_to_optimize[max_idx].get('density', 0.0)
            
            # Zorg dat we kunnen vergelijken; probeer converteren naar float indien nodig
            try:
                d_j_val = float(d_j)
            except Exception:
                d_j_val = 0.0
            try:
                d_max_val = float(d_max)
            except Exception:
                d_max_val = 0.0

            if d_j_val > d_max_val:
                max_idx = j
            j += 1

        # Wissel plaats van i en max_idx als nodig (descending sort)
        if max_idx != i:
            temp = features_to_optimize[i]
            features_to_optimize[i] = features_to_optimize[max_idx]
            features_to_optimize[max_idx] = temp

        i += 1

    # 4) Selectie: vul de knapzak volgens gesorteerde dichtheid
    # Dit is de Greedy 0/1 knapzak benadering.
    selected_features = []
    current_time_used = 0.0
    current_cost_used = 0.0

    k = 0
    while k < len(features_to_optimize):
        item = features_to_optimize[k]
        time_w = item.get('time_weight', 0.0)
        cost_w = item.get('cost_weight', 0.0)

        # Zorg dat time_w en cost_w floats zijn
        try:
            time_w_val = float(time_w)
        except Exception:
            time_w_val = 0.0
        try:
            cost_w_val = float(cost_w)
        except Exception:
            cost_w_val = 0.0

        # Controleer BEIDE constraints: Past de feature nog in de resterende tijd EN in het resterende budget?
        if (current_time_used + time_w_val <= MAX_TIME_CAPACITY) and \
           (current_cost_used + cost_w_val <= MAX_COST_CAPACITY):
            # De feature past, dus selecteer deze en werk de gebruikte capaciteiten bij.
            selected_features.append(item.get('feature'))
            current_time_used += time_w_val
            current_cost_used += cost_w_val
        # Zo niet, dan wordt de feature overgeslagen en gaan we naar de volgende (met lagere dichtheid).

        k += 1

    return selected_features