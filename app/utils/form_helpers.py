# app/utils/form_helpers.py

from flask import session, flash, redirect, url_for
from app.models import Profile, Project, CONFIDENCE_LEVELS, Features_ideas
from app.utils.calculations import calc_ttv_scaled

# -----------------------------------
# LOGIN / ROLE / OWNERSHIP HELPERS
# -----------------------------------

def require_login():
    """Ensures user is logged in, returns user or redirect."""
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    if not user:
        session.clear()
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    return user


def require_role(allowed_roles, user: Profile):
    """
    Ensures user has one of the allowed roles, using case-insensitive comparison.
    """
    # CRUCIALE WIJZIGING: Normaliseer de rol van de gebruiker naar hoofdletters 
    # en normaliseer de lijst van toegestane rollen.
    user_role_upper = user.role.upper()
    allowed_roles_upper = [role.upper() for role in allowed_roles]

    if user_role_upper not in allowed_roles_upper:
        flash("You are not allowed to perform this action.", "danger")
        return redirect(url_for("main.dashboard"))
    return None

def require_company_ownership(obj_company_id: int, user):
    """
    Ensures object belongs to user’s company. 
    Accepts: the object's company ID (int) and the user object (Profile or Response).
    
    NOTE: Added 'isinstance' check to handle non-Profile objects (redirects).
    """
    # CRUCIALE WIJZIGING: Als de user variabele geen Profile object is (maar een Response), 
    # moeten we de crash voorkomen.
    if not isinstance(user, Profile):
        flash("Authorization error: Please log in again.", "danger")
        return redirect(url_for("main.login"))

    if obj_company_id != user.id_company:
        flash("Not allowed.", "danger")
        return redirect(url_for("main.dashboard")) # Stuur naar dashboard, niet projects

    return None

# -----------------------------------
# vectr chart HELPERS
# -----------------------------------
def prepare_vectr_chart_data(project: Project, features_list: list):
    """
    Verwerkt een lijst van features in de genormaliseerde structuur die Chart.js nodig heeft,
    gebruikmakend van de TtV-limits van het Project-object.
    """
    
    # 1. Bepaal de TtV grenzen op basis van het Project-object
    # De maximale TTV is de som van de hoogste TTM en de hoogste TTBV van het project
    local_TTV_MIN = (project.ttm_low_limit or 0.0) + (project.ttbv_low_limit or 0.0)
    local_TTV_MAX = (project.ttm_high_limit or 10.0) + (project.ttbv_high_limit or 0.0) # Gebruik 10.0 als fallback voor de max

    chart_data = []
    
    # 2. Itereren en schalen
    for f in features_list:
        if (
            f.roi_percent is not None
            and f.quality_score is not None
            and f.ttm_weeks is not None
            and f.ttbv_weeks is not None
        ):
            conf = float(f.quality_score)
            effective_ttv = float(f.ttm_weeks) + float(f.ttbv_weeks)

            # Schaling: Gebruik de lokale projectgrenzen
            ttv_scaled = calc_ttv_scaled(
                project.ttm_low_limit, 
                project.ttm_high_limit, 
                project.ttbv_low_limit, 
                project.ttbv_high_limit, 
                effective_ttv
            )

            chart_data.append(
                {
                    "name": f.name_feature,
                    "confidence": conf,
                    "ttv": ttv_scaled,
                    "ttv_weeks": effective_ttv,
                    "roi": float(f.roi_percent),
                    "id": f.id_feature,
                }
            )
    return chart_data

# -----------------------------------
# LOW-LEVEL FIELD PARSERS
# -----------------------------------

def required_str(form, field, errors, label=None, required=True):
    value = form.get(field, "").strip()
    if not value:
        if required:
            errors.append(f"{label or field.replace('_', ' ').title()} is required.")
        return None
    return value


def required_float(form, field, errors, label=None, required=True):
    raw = form.get(field, "").strip()
    if not raw:
        if required:
            errors.append(f"{label or field.replace('_', ' ').title()} is required.")
        return None
    try:
        return float(raw)
    except ValueError:
        errors.append(f"{label or field.replace('_', ' ').title()} must be a number.")
        return None


def required_int(form, field, errors, label=None, required=True):
    raw = form.get(field, "").strip()
    if not raw:
        if required:
            errors.append(f"{label or field.replace('_', ' ').title()} is required.")
        return None
    try:
        return int(raw)
    except ValueError:
        errors.append(f"{label or field.replace('_', ' ').title()} must be an integer.")
        return None

def optional_int_zero(form, field, errors, label=None):
    #Geeft 0 terug als het veld leeg is, valideert integer wanneer er wel invoer is.#
    raw = form.get(field, "").strip()
    if not raw:
        return 0  # Geen waarde ingevuld? Maak er automatisch 0 van zodat de gebruiker niets hoeft te typen.
    try:
        return int(raw)  # Wel een waarde: probeer deze te converteren naar een integer.
    except ValueError:
        errors.append(f"{label or field.replace('_', ' ').title()} must be an integer.")
        return None


def optional_float_zero(form, field, errors, label=None):
    #Geeft 0.0 terug als het veld leeg is, valideert float wanneer er wel invoer is.#
    raw = form.get(field, "").strip()
    if not raw:
        return 0.0  # Leeg laten wordt automatisch 0.0 zodat optionele velden de flow niet blokkeren.
    try:
        return float(raw)  # Invoer aanwezig: converteer naar float.
    except ValueError:
        errors.append(f"{label or field.replace('_', ' ').title()} must be a number.")
        return None


# -----------------------------------
# OBJECT-LEVEL PARSERS
# -----------------------------------

def parse_project_form(form):
    errors = []
    name = required_str(form, "project_name", errors, label="Project name")
    
    # NIEUW: TTV LIMITS OPHALEN
    ttm_low = optional_float_zero(form, "ttm_low_limit", errors, label="Lowest TTM")
    ttm_high = required_float(form, "ttm_high_limit", errors, label="Highest TTM")
    ttbv_low = optional_float_zero(form, "ttbv_low_limit", errors, label="Lowest TTBV")
    ttbv_high = required_float(form, "ttbv_high_limit", errors, label="Highest TTBV")
    
    return {
        "project_name": name,
        "ttm_low_limit": ttm_low,
        "ttm_high_limit": ttm_high,
        "ttbv_low_limit": ttbv_low,
        "ttbv_high_limit": ttbv_high,
    }, errors

def parse_feature_form(form):
    errors = []

    name_feature = required_str(form, "name_feature", errors, label="Title")
    description = form.get("description", "").strip() or None

    data = {
        "name_feature": name_feature,
        "description": description,
        "extra_revenue": required_int(form, "extra_revenue", errors),
        "churn_reduction": optional_int_zero(form, "churn_reduction", errors),
        "cost_savings": optional_int_zero(form, "cost_savings", errors),
        "investment_hours": required_int(form, "investment_hours", errors),
        "hourly_rate": required_int(form, "hourly_rate", errors),
        "opex_hours": optional_int_zero(form, "opex_hours", errors),
        "other_costs": optional_int_zero(form, "other_costs", errors),
        "horizon": required_int(form, "horizon", errors),
        "ttm_weeks": required_int(form, "ttm_weeks", errors),
        "ttbv_weeks": required_int(form, "ttbv_weeks", errors),
        "quality_score": required_float(form, "quality_score", errors, required=False),
    }

    return data, errors


def parse_roadmap_form(form):
    errors = []
        # Met floats kunnen we decimalen opslaan (bijv. 2.5 personen of 3.75 punten)
    return {
        "start_roadmap": required_str(form, "start_roadmap", errors),
        "end_roadmap": required_str(form, "end_roadmap", errors),
        "time_capacity": required_float(form, "time_capacity", errors),
        "budget_allocation": required_float(form, "budget_allocation", errors),
    }, errors


def parse_milestone_form(form):
    errors = []
    return {
        "name": required_str(form, "name", errors),
        "start_date": form.get("start_date") or None,
        "end_date": form.get("end_date") or None,
        "goal": form.get("goal") or None,
        "status": form.get("status") or None,
    }, errors


def parse_evidence_form(form):
    errors = []

    title = required_str(form, "title", errors, label="Title")
    type_select = required_str(form, "type_select", errors, label="Evidence type")
    custom_type = form.get("custom_type", "").strip()

    final_type = custom_type if (type_select == "Other" and custom_type) else type_select

    source = required_str(form, "source", errors)
    description = required_str(form, "description", errors)
    attachment_url = form.get("attachment_url", "").strip() or None

    conf_raw = form.get("new_confidence", "").strip()
    allowed_values = {v for (v, _) in CONFIDENCE_LEVELS}

    new_conf = None
    if not conf_raw:
        errors.append("Confidence level is required.")
    else:
        try:
            new_conf = float(conf_raw)
        except ValueError:
            errors.append("Confidence must be a number.")

    if new_conf not in allowed_values:
        errors.append("Invalid confidence selected.")

    return {
        "title": title,
        "final_type": final_type,
        "source": source,
        "description": description,
        "attachment_url": attachment_url,
        "new_confidence": new_conf,
    }, errors


# -----------------------------------
# CONFIDENCE RECOMPUTE
# -----------------------------------

def recompute_feature_confidence(feature):
    if not feature.evidence:
        return None
    scores = [e.new_confidence for e in feature.evidence]
    return max(scores) if scores else None
