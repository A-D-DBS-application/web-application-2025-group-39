# app/utils/form_helpers.py

from flask import session, flash, redirect, url_for
from app.models import Profile, CONFIDENCE_LEVELS, Features_ideas
from app.utils.calculations import calc_roi, calc_ttv

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
    """Ensures user has one of the allowed roles."""
    if user.role not in allowed_roles:
        flash("You are not allowed to perform this action.", "danger")
        return redirect(url_for("main.dashboard"))
    return None


def require_company_ownership(obj_company_id: int, user: Profile):
    """Ensures object belongs to user’s company."""
    if obj_company_id != user.id_company:
        flash("Not allowed.", "danger")
        return redirect(url_for("main.dashboard"))
    return None

# -----------------------------------
# vectr chart HELPERS
# -----------------------------------
def prepare_vectr_chart_data(features_list):
    """
    Verwerkt een lijst van features in de genormaliseerde structuur die Chart.js nodig heeft,
    inclusief TtV-normalisatie (schaling).
    """
    valid_ttv = []
    for f in features_list:
        if (
            f.ttm_low is not None
            and f.ttbv_low is not None
            and f.ttm_high is not None
            and f.ttbv_high is not None
        ):
            min_ttv = float(f.ttm_low) + float(f.ttbv_low)
            max_ttv = float(f.ttm_high) + float(f.ttbv_high)
            valid_ttv.append((min_ttv, max_ttv))

    if valid_ttv:
        local_TTV_MIN = min(m for m, _ in valid_ttv)
        local_TTV_MAX = max(M for _, M in valid_ttv)
    else:
        local_TTV_MIN, local_TTV_MAX = 0.0, 10.0

    chart_data = []
    for f in features_list:
        if (
            f.roi_percent is not None
            and f.quality_score is not None
            and f.ttm_weeks is not None
            and f.ttbv_weeks is not None
        ):
            conf = float(f.quality_score)
            effective_ttv = float(f.ttm_weeks) + float(f.ttbv_weeks)

            if local_TTV_MAX > local_TTV_MIN:
                ttv_norm = (effective_ttv - local_TTV_MIN) / (
                    local_TTV_MAX - local_TTV_MIN
                ) * 10
                ttv_scaled = 10.0 - ttv_norm
            else:
                ttv_scaled = 0

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


# -----------------------------------
# OBJECT-LEVEL PARSERS
# -----------------------------------

def parse_project_form(form):
    errors = []
    name = required_str(form, "project_name", errors, label="Project name")
    return {"project_name": name}, errors


def parse_feature_form(form):
    errors = []

    name_feature = required_str(form, "name_feature", errors, label="Title")
    description = form.get("description", "").strip() or None

    data = {
        "name_feature": name_feature,
        "description": description,
        "extra_revenue": required_int(form, "extra_revenue", errors),
        "churn_reduction": required_int(form, "churn_reduction", errors),
        "cost_savings": required_int(form, "cost_savings", errors),
        "investment_hours": required_int(form, "investment_hours", errors),
        "hourly_rate": required_int(form, "hourly_rate", errors),
        "opex_hours": required_int(form, "opex_hours", errors),
        "other_costs": required_int(form, "other_costs", errors),
        "horizon": required_int(form, "horizon", errors),
        "ttm_weeks": required_int(form, "ttm_weeks", errors),
        "ttbv_weeks": required_int(form, "ttbv_weeks", errors),
        "ttm_low": required_float(form, "ttm_low", errors),
        "ttm_high": required_float(form, "ttm_high", errors),
        "ttbv_low": required_float(form, "ttbv_low", errors),
        "ttbv_high": required_float(form, "ttbv_high", errors),
        "quality_score": required_float(form, "quality_score", errors, required=False),
    }

    return data, errors

def update_feature_data(feature_object: Features_ideas, data: dict):
    """
    Werkt het Features_ideas object bij met geparste formulierdata en berekent
    ROI en TTV opnieuw.

    Dit centraliseert de toewijzings- en berekeningslogica, wat duplicatie
    tussen 'add_feature' en 'edit_feature' voorkomt (DRY Best Practice).
    
    :param feature_object: De Features_ideas (FeatureIdea) instantie (nieuw of bestaand).
    :param data: Een dictionary met geparste formuliergegevens van parse_feature_form.
    """
    # 1. Toewijzen van alle inputvelden
    feature_object.name_feature = data["name_feature"]
    feature_object.description = data["description"]
    
    # ROI VELDEN
    feature_object.extra_revenue = data["extra_revenue"]
    feature_object.churn_reduction = data["churn_reduction"]
    feature_object.cost_savings = data["cost_savings"]
    feature_object.investment_hours = data["investment_hours"]
    feature_object.hourly_rate = data["hourly_rate"]
    feature_object.opex_hours = data["opex_hours"]
    feature_object.other_costs = data["other_costs"]
    feature_object.horizon = data["horizon"]
    
    # TTV VELDEN
    feature_object.ttm_weeks = data["ttm_weeks"]
    feature_object.ttbv_weeks = data["ttbv_weeks"]
    feature_object.ttm_low = data["ttm_low"]
    feature_object.ttm_high = data["ttm_high"]
    feature_object.ttbv_low = data["ttbv_low"]
    feature_object.ttbv_high = data["ttbv_high"]
    
    # CONFIDENCE VELD
    feature_object.quality_score = data["quality_score"]

    # 2. Herbereken afgeleide waarden (ROI en TTV)
    feature_object.roi_percent = calc_roi(
        feature_object.extra_revenue,
        feature_object.churn_reduction,
        feature_object.cost_savings,
        feature_object.investment_hours,
        feature_object.hourly_rate,
        feature_object.opex_hours,
        feature_object.other_costs,
    )
    feature_object.ttv_weeks = calc_ttv(feature_object.ttm_weeks, feature_object.ttbv_weeks)


def parse_roadmap_form(form):
    errors = []
    return {
        "start_quarter": required_str(form, "start_quarter", errors),
        "end_quarter": required_str(form, "end_quarter", errors),
        "team_size": required_int(form, "team_size", errors),
        "sprint_capacity": required_int(form, "sprint_capacity", errors),
        "budget_allocation": required_int(form, "budget_allocation", errors),
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
