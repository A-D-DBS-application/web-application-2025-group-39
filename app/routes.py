from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    send_file,
    Response,
)
from app import db
from app.models import (
    Profile,
    Company,
    Project,
    Features_ideas,
    Roadmap,
    Milestone,
    Evidence,
    Decision,
    CONFIDENCE_LEVELS,
)

import uuid
import datetime
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches

from app.constants import (
    CONF_MIN,
    CONF_LOW_THRESHOLD,
    CONF_MID_HIGH_THRESHOLD,
    CONF_MAX,
    TTV_MIN,
    TTV_SLOW_THRESHOLD,
    TTV_MID_THRESHOLD,
    TTV_MAX,
)

from app.utils.calculations import calc_roi, calc_ttv, to_numeric
from app.utils.form_helpers import (
    require_login,
    require_role,
    require_company_ownership,
    parse_project_form,
    parse_feature_form,
    parse_roadmap_form,
    parse_milestone_form,
    parse_evidence_form,
    recompute_feature_confidence,
)

# Blueprint
main = Blueprint("main", __name__)


# ==============================
# INDEX
# ==============================
@main.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


# ==============================
# LOGIN
# ==============================
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").lower().strip()
        password = request.form.get("password") or ""

        user = Profile.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id_profile
            session["name"] = user.name
            session["role"] = user.role
            flash("Successfully logged in!", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ==============================
# REGISTER
# ==============================
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = (request.form.get("email") or "").lower().strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        company_name = request.form.get("company_name", "").strip()

        if not all([name, email, password, role, company_name]):
            flash("All fields are required.", "danger")
            return render_template("register.html")

        try:
            # Find or create company
            company = db.session.execute(
                db.text(
                    "SELECT * FROM public.company WHERE company_name = :company_name LIMIT 1"
                ),
                {"company_name": company_name},
            ).fetchone()

            if not company:
                db.session.execute(
                    db.text(
                        "INSERT INTO public.company (company_name) VALUES (:company_name)"
                    ),
                    {"company_name": company_name},
                )
                db.session.commit()
                company = db.session.execute(
                    db.text(
                        "SELECT * FROM public.company WHERE company_name = :company_name LIMIT 1"
                    ),
                    {"company_name": company_name},
                ).fetchone()

            new_user = Profile(
                name=name,
                email=email,
                role=role,
                id_company=company.id_company,
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("main.login"))

        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {e}")
            flash("An error occurred during registration.", "danger")

    return render_template("register.html")


# ==============================
# DASHBOARD
# ==============================
@main.route("/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    name = session.get("name")
    role = session.get("role")
    return render_template("dashboard.html", name=name, role=role)


# ==============================
# LOGOUT
# ==============================
@main.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


# ==============================
# PROFILE
# ==============================
@main.route("/profile")
def profile():
    user = require_login()
    if not isinstance(user, Profile):
        return user  # redirect

    company = Company.query.get(user.id_company)
    return render_template(
        "profile.html",
        name=user.name,
        email=user.email,
        company=company.company_name if company else "N/A",
        role=user.role,
    )


# ==============================
# PROJECTS OVERVIEW
# ==============================
@main.route("/projects")
def projects():
    user = require_login()
    if not isinstance(user, Profile):
        return user

    projects = (
        db.session.query(Project, Company.company_name)
        .join(Company, Project.id_company == Company.id_company)
        .filter(Project.id_company == user.id_company)
        .order_by(Project.id_project.desc())
        .all()
    )
    return render_template("projects.html", projects=projects)


# ==============================
# ADD PROJECT
# ==============================
@main.route("/add_project", methods=["GET", "POST"])
def add_project():
    user = require_login()
    if not isinstance(user, Profile):
        return user

    # Only founder/PM
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect

    user_company = Company.query.get(user.id_company)

    if request.method == "POST":
        data, errors = parse_project_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_project.html", company=user_company)

        new_project = Project(
            project_name=data["project_name"],
            id_company=user_company.id_company,
        )
        db.session.add(new_project)
        db.session.commit()

        flash("Project added successfully.", "success")
        return redirect(url_for("main.projects"))

    return render_template("add_project.html", company=user_company)


# ==============================
# EDIT PROJECT
# ==============================
@main.route("/projects/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)

    # Only founder/PM + same company
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    if request.method == "POST":
        data, errors = parse_project_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("edit_project.html", project=project)

        project.project_name = data["project_name"]
        db.session.commit()

        flash("Project updated successfully.", "success")
        return redirect(url_for("main.projects"))

    return render_template("edit_project.html", project=project)


# ==============================
# DELETE PROJECT
# ==============================
@main.route("/projects/delete/<int:project_id>", methods=["POST"])
def delete_project(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)

    # Only founder/PM + same company
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    try:
        db.session.delete(project)
        db.session.commit()
        flash("Project deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting project: {e}")
        flash("An error occurred while deleting the project.", "danger")

    return redirect(url_for("main.projects"))


# ==============================
# ADD FEATURE
# ==============================
@main.route("/projects/<int:project_id>/add-feature", methods=["GET", "POST"])
def add_feature(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    # Only founder/PM
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect

    project = Project.query.get_or_404(project_id)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    company = project.company

    if request.method == "POST":
        data, errors = parse_feature_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_feature.html", project=project, company=company)

        roi_percent = calc_roi(
            data["extra_revenue"],
            data["churn_reduction"],
            data["cost_savings"],
            data["investment_hours"],
            data["hourly_rate"],
            data["opex_hours"],
            data["other_costs"],
        )
        ttv_weeks = calc_ttv(data["ttm_weeks"], data["ttbv_weeks"])

        new_feature = Features_ideas(
            id_feature=str(uuid.uuid4()),
            id_company=company.id_company,
            id_project=project.id_project,
            name_feature=data["name_feature"],
            description=data["description"],
            extra_revenue=data["extra_revenue"],
            churn_reduction=data["churn_reduction"],
            cost_savings=data["cost_savings"],
            investment_hours=data["investment_hours"],
            hourly_rate=data["hourly_rate"],
            opex_hours=data["opex_hours"],
            other_costs=data["other_costs"],
            horizon=data["horizon"],
            ttm_weeks=data["ttm_weeks"],
            ttbv_weeks=data["ttbv_weeks"],
            ttm_low=data["ttm_low"],
            ttm_high=data["ttm_high"],
            ttbv_low=data["ttbv_low"],
            ttbv_high=data["ttbv_high"],
            roi_percent=roi_percent,
            ttv_weeks=ttv_weeks,
            quality_score=data["quality_score"],
        )

        db.session.add(new_feature)
        db.session.commit()

        flash("Feature saved successfully.", "success")
        return redirect(url_for("main.projects"))

    return render_template("add_feature.html", project=project, company=company)


# ==================================
# LIVE CALC: ROI
# ==================================
@main.route("/features/calc/roi", methods=["POST"])
def features_calc_roi():
    roi_percent_raw = calc_roi(
        request.form.get("extra_revenue"),
        request.form.get("churn_reduction"),
        request.form.get("cost_savings"),
        request.form.get("investment_hours"),
        request.form.get("hourly_rate"),
        request.form.get("opex_hours"),
        request.form.get("other_costs"),
    )

    roi_percent = roi_percent_raw if roi_percent_raw is not None else 0.0
    return render_template("features/_roi_partial.html", roi_percent=roi_percent)


# ==================================
# LIVE CALC: TTV
# ==================================
@main.route("/features/calc/ttv", methods=["POST"])
def features_calc_ttv():
    ttv_weeks_raw = calc_ttv(
        request.form.get("ttm_weeks"),
        request.form.get("ttbv_weeks"),
    )
    ttv_weeks_result = ttv_weeks_raw if ttv_weeks_raw is not None else 0.0
    return render_template("features/_ttv_partial.html", ttv_weeks=ttv_weeks_result)


# ==============================
# VIEW FEATURES
# ==============================
@main.route("/projects/<int:project_id>/features", methods=["GET"])
def view_features(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    company = Company.query.get(user.id_company)

    user_role = session.get("role")
    can_sort = user_role == "PM"

    if can_sort:
        sort_by = request.args.get("sort_by", "roi")
        direction = request.args.get("direction", "desc")
    else:
        sort_by = "name"
        direction = "asc"

    features_query = Features_ideas.query.filter_by(id_project=project_id)

    if sort_by == "roi":
        column = Features_ideas.roi_percent
    elif sort_by == "ttv":
        column = Features_ideas.ttm_weeks
    elif sort_by == "confidence":
        column = Features_ideas.quality_score
    else:
        column = Features_ideas.name_feature

    if direction == "desc":
        features = features_query.order_by(column.desc()).all()
    else:
        features = features_query.order_by(column.asc()).all()

    # Compute VECTR score
    for f in features:
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        vectr_score = ttv_weeks * roi_percent * confidence_score
        setattr(f, "vectr_score", round(vectr_score, 2))

    return render_template(
        "view_features.html",
        project=project,
        features=features,
        company=company,
        current_sort=sort_by,
        current_direction=direction,
        can_sort=can_sort,
    )


# ==============================
# EDIT FEATURE
# ==============================
@main.route("/feature/<uuid:feature_id>/edit", methods=["GET", "POST"])
def edit_feature(feature_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    feature = Features_ideas.query.get_or_404(str(feature_id))
    project = Project.query.get_or_404(feature.id_project)
    company = Company.query.get(project.id_company)

    # Only founder/PM + ownership
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    if request.method == "POST":
        data, errors = parse_feature_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "edit_feature.html",
                feature=feature,
                project=project,
                company=company,
            )

        feature.name_feature = data["name_feature"]
        feature.description = data["description"]
        feature.extra_revenue = data["extra_revenue"]
        feature.churn_reduction = data["churn_reduction"]
        feature.cost_savings = data["cost_savings"]
        feature.investment_hours = data["investment_hours"]
        feature.hourly_rate = data["hourly_rate"]
        feature.opex_hours = data["opex_hours"]
        feature.other_costs = data["other_costs"]
        feature.horizon = data["horizon"]
        feature.ttm_weeks = data["ttm_weeks"]
        feature.ttbv_weeks = data["ttbv_weeks"]
        feature.ttm_low = data["ttm_low"]
        feature.ttm_high = data["ttm_high"]
        feature.ttbv_low = data["ttbv_low"]
        feature.ttbv_high = data["ttbv_high"]
        feature.quality_score = data["quality_score"]

        feature.roi_percent = calc_roi(
            feature.extra_revenue,
            feature.churn_reduction,
            feature.cost_savings,
            feature.investment_hours,
            feature.hourly_rate,
            feature.opex_hours,
            feature.other_costs,
        )
        feature.ttv_weeks = calc_ttv(feature.ttm_weeks, feature.ttbv_weeks)

        db.session.commit()
        flash("Feature updated successfully!", "success")
        return redirect(url_for("main.view_features", project_id=feature.id_project))

    return render_template(
        "edit_feature.html", feature=feature, project=project, company=company
    )


# ==============================
# DELETE FEATURE
# ==============================
@main.route("/feature/<uuid:feature_id>/delete", methods=["POST"])
def delete_feature(feature_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    feature = Features_ideas.query.get_or_404(str(feature_id))
    project = Project.query.get_or_404(feature.id_project)

    # Only founder/PM + ownership
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    project_id = feature.id_project
    db.session.delete(feature)
    db.session.commit()
    flash("Feature deleted successfully!", "success")
    return redirect(url_for("main.view_features", project_id=project_id))


# ==============================
# VECTR CHART (WEB)
# ==============================
@main.route("/projects/<int:project_id>/vectr-chart", methods=["GET"])
def vectr_chart(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    features = Features_ideas.query.filter_by(id_project=project_id).all()

    valid_ttv = []
    for f in features:
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
    for f in features:
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

    return render_template("vectr_chart.html", project=project, chart_data=chart_data)


# ==============================
# ROADMAP ROUTES
# ==============================
@main.route("/roadmap/add/<int:project_id>", methods=["GET", "POST"])
def add_roadmap(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    # Only founders can create roadmaps
    role_redirect = require_role(["founder"], user)
    if role_redirect:
        return role_redirect

    project = Project.query.get_or_404(project_id)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    # MAX 1 ROADMAP PER PROJECT
    existing = Roadmap.query.filter_by(id_project=project_id).first()
    if existing:
        flash("This project already has a roadmap.", "danger")
        return redirect(url_for("main.roadmap_overview", project_id=project_id))

    if request.method == "POST":
        data, errors = parse_roadmap_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_roadmap.html", project=project)

        roadmap = Roadmap(id_project=project_id, **data)
        db.session.add(roadmap)
        db.session.commit()

        flash("Roadmap created successfully!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=project_id))

    return render_template("add_roadmap.html", project=project)


@main.route("/roadmap/<int:project_id>")
def roadmap_overview(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    # Roadmaps sorted by start_quarter (string sort works for "Qn YYYY")
    roadmaps = (
        Roadmap.query.filter_by(id_project=project_id)
        .order_by(Roadmap.start_quarter.asc())
        .all()
    )

    # Sort milestones inside each roadmap by start_date
    for roadmap in roadmaps:
        roadmap.milestones.sort(
            key=lambda m: m.start_date if m.start_date else datetime.date.max
        )

    return render_template(
        "roadmap_overview.html",
        project=project,
        roadmaps=roadmaps,
    )


@main.route("/roadmap/edit/<int:roadmap_id>", methods=["GET", "POST"])
def edit_roadmap(roadmap_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    # Only founders may edit
    role_redirect = require_role(["founder"], user)
    if role_redirect:
        return role_redirect

    roadmap = Roadmap.query.get_or_404(roadmap_id)
    project = Project.query.get_or_404(roadmap.id_project)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    if request.method == "POST":
        data, errors = parse_roadmap_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("edit_roadmap.html", roadmap=roadmap, project=project)

        roadmap.start_quarter = data["start_quarter"]
        roadmap.end_quarter = data["end_quarter"]
        roadmap.team_size = data["team_size"]
        roadmap.sprint_capacity = data["sprint_capacity"]
        roadmap.budget_allocation = data["budget_allocation"]

        db.session.commit()

        flash("Roadmap updated successfully!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=project.id_project))

    return render_template("edit_roadmap.html", roadmap=roadmap, project=project)


# ==============================
# MILESTONES ROUTES
# ==============================

@main.route("/milestone/add/<int:roadmap_id>", methods=["GET", "POST"])
def add_milestone(roadmap_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    # founder / PM only
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect

    roadmap = Roadmap.query.get_or_404(roadmap_id)
    project = Project.query.get_or_404(roadmap.id_project)

    # Company check
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    # Load all features for this project
    features = Features_ideas.query.filter_by(id_project=project.id_project).all()

    # Compute VECTR score for each feature
    for f in features:
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        vectr_score = ttv_weeks * roi_percent * confidence_score
        setattr(f, "vectr_score", round(vectr_score, 2))

    # Sort features descending by score
    features = sorted(features, key=lambda x: getattr(x, "vectr_score", 0), reverse=True)

    if request.method == "POST":
        data, errors = parse_milestone_form(request.form)

        if errors:
            for e in errors:
                flash(e, "danger")

            return render_template(
                "add_milestone.html",
                roadmap=roadmap,
                features=features,
                selected_features=request.form.getlist("features"),
            )

        milestone = Milestone(
            id_roadmap=roadmap_id,
            name=data["name"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            goal=data["goal"],
            status=data["status"],
        )

        selected = request.form.getlist("features")
        milestone.features = Features_ideas.query.filter(
            Features_ideas.id_feature.in_(selected)
        ).all()

        db.session.add(milestone)
        db.session.commit()

        flash("Milestone added!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    return render_template(
        "add_milestone.html",
        roadmap=roadmap,
        features=features,
        selected_features=[],
    )




@main.route("/milestone/edit/<int:milestone_id>", methods=["GET", "POST"])
def edit_milestone(milestone_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    # founder / PM only
    role_redirect = require_role(["founder", "PM"], user)
    if role_redirect:
        return role_redirect

    milestone = Milestone.query.get_or_404(milestone_id)
    roadmap = Roadmap.query.get_or_404(milestone.id_roadmap)
    project = Project.query.get_or_404(roadmap.id_project)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    # Load features for this project
    features = Features_ideas.query.filter_by(id_project=project.id_project).all()

    # Compute VECTR score for features
    for f in features:
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        vectr_score = ttv_weeks * roi_percent * confidence_score
        setattr(f, "vectr_score", round(vectr_score, 2))

    # Sort features descending
    features = sorted(features, key=lambda x: getattr(x, "vectr_score", 0), reverse=True)

    # Get selected features for prefill
    existing_selected = [f.id_feature for f in milestone.features]

    if request.method == "POST":
        data, errors = parse_milestone_form(request.form)

        if errors:
            for e in errors:
                flash(e, "danger")

            return render_template(
                "edit_milestone.html",
                milestone=milestone,
                features=features,
                selected_features=request.form.getlist("features"),
            )

        milestone.name = data["name"]
        milestone.start_date = data["start_date"]
        milestone.end_date = data["end_date"]
        milestone.goal = data["goal"]
        milestone.status = data["status"]

        selected = request.form.getlist("features")
        milestone.features = Features_ideas.query.filter(
            Features_ideas.id_feature.in_(selected)
        ).all()

        db.session.commit()
        flash("Milestone updated!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    return render_template(
        "edit_milestone.html",
        milestone=milestone,
        features=features,
        selected_features=existing_selected,
    )




@main.route("/milestone/delete/<int:milestone_id>", methods=["POST"])
def delete_milestone(milestone_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    milestone = Milestone.query.get_or_404(milestone_id)
    roadmap = Roadmap.query.get_or_404(milestone.id_roadmap)
    project = Project.query.get_or_404(roadmap.id_project)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    db.session.delete(milestone)
    db.session.commit()
    flash("Milestone deleted!", "success")

    return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))


# ==============================
# EVIDENCE: ADD
# ==============================
@main.route("/feature/<feature_id>/add-evidence", methods=["GET", "POST"])
def add_evidence(feature_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    feature = Features_ideas.query.get_or_404(feature_id)
    project = Project.query.get_or_404(feature.id_project)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    if request.method == "POST":
        data, errors = parse_evidence_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "add_evidence.html",
                feature=feature,
                CONFIDENCE_LEVELS=CONFIDENCE_LEVELS,
            )

        old_conf = feature.quality_score or 0.0

        ev = Evidence(
            id_company=user.id_company,
            id_feature=feature_id,
            title=data["title"],
            type=data["final_type"],
            source=data["source"],
            description=data["description"],
            attachment_url=data["attachment_url"],
            old_confidence=old_conf,
            new_confidence=data["new_confidence"],
        )

        db.session.add(ev)
        db.session.flush()  # so feature.evidence includes this one

        new_score = recompute_feature_confidence(feature)
        feature.quality_score = new_score if new_score is not None else old_conf

        db.session.commit()
        flash("Evidence added!", "success")
        return redirect(url_for("main.view_evidence", feature_id=feature_id))

    return render_template(
        "add_evidence.html",
        feature=feature,
        CONFIDENCE_LEVELS=CONFIDENCE_LEVELS,
    )


# ==============================
# EVIDENCE: LIST
# ==============================
@main.route("/feature/<feature_id>/evidence")
def view_evidence(feature_id):
    user = require_login()
    if isinstance(user, Response):  # redirect
        return user

    feature = Features_ideas.query.get_or_404(feature_id)

    evidence_list = Evidence.query.filter_by(id_feature=feature_id) \
        .order_by(Evidence.new_confidence.desc()) \
        .all()

    # Convert [(value, label), ...] → {value: label}
    CONFIDENCE_LABELS = {v: label for (v, label) in CONFIDENCE_LEVELS}

    return render_template(
        "view_evidence.html",
        feature=feature,
        evidence_list=evidence_list,
        CONFIDENCE_LABELS=CONFIDENCE_LABELS
    )




# ==============================
# EVIDENCE: DELETE
# ==============================
@main.route("/evidence/<int:evidence_id>/delete", methods=["POST"])
def delete_evidence(evidence_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    ev = Evidence.query.get_or_404(evidence_id)
    feature = Features_ideas.query.get_or_404(ev.id_feature)
    project = Project.query.get_or_404(feature.id_project)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    fallback_old = ev.old_confidence or 0.0

    db.session.delete(ev)
    db.session.flush()

    new_score = recompute_feature_confidence(feature)
    if new_score is None:
        feature.quality_score = fallback_old
    else:
        feature.quality_score = new_score

    db.session.commit()

    flash("Evidence deleted!", "success")
    return redirect(url_for("main.view_evidence", feature_id=feature.id_feature))


# ==============================
# EVIDENCE: EDIT
# ==============================
@main.route("/evidence/<int:evidence_id>/edit", methods=["GET", "POST"])
def edit_evidence(evidence_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    ev = Evidence.query.get_or_404(evidence_id)
    feature = Features_ideas.query.get_or_404(ev.id_feature)
    project = Project.query.get_or_404(feature.id_project)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    if request.method == "POST":
        data, errors = parse_evidence_form(request.form)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "edit_evidence.html",
                evidence=ev,
                feature=feature,
                CONFIDENCE_LEVELS=CONFIDENCE_LEVELS,
            )

        ev.title = data["title"]
        ev.type = data["final_type"]
        ev.source = data["source"]
        ev.description = data["description"]
        ev.attachment_url = data["attachment_url"]
        ev.new_confidence = data["new_confidence"]

        db.session.flush()
        new_score = recompute_feature_confidence(feature)
        feature.quality_score = new_score if new_score is not None else 0.0

        db.session.commit()
        flash("Evidence updated!", "success")
        return redirect(url_for("main.view_evidence", feature_id=feature.id_feature))

    return render_template(
        "edit_evidence.html",
        evidence=ev,
        feature=feature,
        CONFIDENCE_LEVELS=CONFIDENCE_LEVELS,
    )


# ==============================
# VECTR CHART PDF
# ==============================
@main.route("/projects/<int:project_id>/vectr-chart/pdf")
def vectr_chart_pdf(project_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    features = Features_ideas.query.filter_by(id_project=project_id).all()

    valid_ttv = []
    for f in features:
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

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(0.0, 10.0)

    zones = [
        {"color": (1, 0, 0, 0.25), "x": 0.0, "y": 0.0, "w": 7.0, "h": 5.0},
        {"color": (1, 140/255, 0, 0.25), "x": 1.0, "y": 5.0, "w": 6.0, "h": 5.0},
        {"color": (1, 0, 0, 0.25), "x": 0.0, "y": 5.0, "w": 1.0, "h": 5.0},
        {"color": (0, 150/255, 0, 0.25), "x": 7.0, "y": 7.0, "w": 3.0, "h": 3.0},
        {"color": (144/255, 238/255, 144/255, 0.25), "x": 7.0, "y": 5.0, "w": 3.0, "h": 2.0},
        {"color": (1, 165/255, 0, 0.25), "x": 7.0, "y": 0.0, "w": 3.0, "h": 5.0},
    ]

    for z in zones:
        rect = patches.Rectangle(
            (z["x"], z["y"]),
            z["w"],
            z["h"],
            facecolor=z["color"],
            edgecolor=(0, 0, 0, 0.4),
            linewidth=0.5,
        )
        ax.add_patch(rect)

    def get_zone_color_mpl(confidence, ttv_scaled):
        x_low = CONF_LOW_THRESHOLD
        x_high = CONF_MID_HIGH_THRESHOLD
        y_slow = TTV_SLOW_THRESHOLD
        y_fast = TTV_MID_THRESHOLD

        if confidence >= x_high:
            if ttv_scaled >= y_fast:
                return (0, 150/255, 0, 1)
            elif y_slow <= ttv_scaled < y_fast:
                return (144/255, 238/255, 144/255, 1)
            else:
                return (1, 165/255, 0, 1)
        else:
            if ttv_scaled < y_slow:
                return (1, 0, 0, 1)
            elif confidence < x_low:
                return (1, 0, 0, 1)
            else:
                return (1, 140/255, 0, 1)

    scatter_x = []
    scatter_y = []
    scatter_s = []
    scatter_c = []
    scatter_labels = []

    for f in features:
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

            roi_val = float(f.roi_percent)
            size_mpl_area = max(50, min(2000, max(0, roi_val) * 15))
            color = get_zone_color_mpl(conf, ttv_scaled)

            scatter_x.append(conf)
            scatter_y.append(ttv_scaled)
            scatter_s.append(size_mpl_area)
            scatter_c.append(color)
            scatter_labels.append(f.name_feature)

    ax.scatter(
        scatter_x,
        scatter_y,
        s=scatter_s,
        c=scatter_c,
        edgecolors="black",
        linewidths=1.0,
        alpha=0.8,
    )

    ax.set_xticks([0, 1, 3, 5, 7, 8, 10])
    ax.set_xticklabels(["0", "Low", "3", "5", "7", "High", "10"])
    ax.set_yticks([0, 1, 2, 3, 5, 7, 8, 10])
    ax.set_yticklabels(["0", "1", "Slow", "3", "5", "7", "Fast", "10"])

    ax.set_xlabel("Confidence")
    ax.set_ylabel("Time-to-Value (TtV)")
    ax.set_title(f"VECTR Prioritization Chart for {project.project_name}")

    for i, label in enumerate(scatter_labels):
        ax.annotate(
            label,
            (scatter_x[i], scatter_y[i]),
            textcoords="offset points",
            xytext=(5, -5),
            ha="left",
            fontsize=7,
        )

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format="pdf")
    plt.close(fig)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name=f"vectr_chart_{project.project_name}.pdf",
        mimetype="application/pdf",
    )


# ==============================
# FEATURE DECISION ROUTE 
# ==============================
@main.route("/set_feature_decision/<string:feature_id>/<string:decision_value>", methods=["POST"])
def set_feature_decision(feature_id, decision_value):
    # 1) Login check
    if "user_id" not in session:
        flash("U moet inloggen om beslissingen te maken.", "danger")
        return redirect(url_for("main.login"))

    # 2) Haal user + feature op
    user = Profile.query.get(session["user_id"])
    feature = Features_ideas.query.get_or_404(feature_id)

    # 3) Security: feature moet bij dezelfde company horen
    if feature.id_company != user.id_company:
        flash("Niet toegestaan.", "danger")
        return redirect(url_for("main.projects"))

    # 4) Map Yes/No naar decision types (matcht met je CSS: decision-approved / decision-rejected)
    if decision_value == "Yes":
        decision_type = "Approved"
    elif decision_value == "No":
        decision_type = "Rejected"
    else:
        decision_type = "Pending"

    # 5) Nieuwe Decision record opslaan
    try:
        d = Decision(
            id_feature=feature.id_feature,
            id_company=user.id_company,
            decision_type=decision_type,
            reasoning=None,
        )
        db.session.add(d)
        db.session.commit()

        flash(f"Beslissing opgeslagen: {decision_type}", "success")
        return redirect(url_for("main.view_features", project_id=feature.id_project))

    except Exception as e:
        db.session.rollback()
        print(f"Fout bij het instellen van de beslissing: {e}")
        flash("Er is een fout opgetreden bij het verwerken van de beslissing.", "danger")
        return redirect(url_for("main.view_features", project_id=feature.id_project))



#route voor deraction balk:
@main.route("/project/<string:project_id>") 
def project_detail(project_id):
    # 1. Haal het Project object op
    project = Project.query.filter_by(id_project=project_id).first_or_404()
    
    # 2. Haal alle features op die bij dit project horen
    features = Features_ideas.query.filter_by(id_project=project_id).all()

    # 3. Render de view_features template (die je al hebt)
    # Zorg dat de template de benodigde variabelen krijgt
    return render_template(
        "view_features.html", 
        project=project, 
        features=features
    )
# Dit is een Context Processor. Het injecteert de user_projects variabele in ALLE templates.
@main.context_processor
def inject_user_projects():
    user_projects = []
    user_id = session.get("user_id")
    
    if user_id:
        # Stap 1: Zoek de user zijn Profile om de id_company te vinden
        # We gaan ervan uit dat id_profile overeenkomt met de user_id in de sessie
        profile = Profile.query.filter_by(id_profile=user_id).first() 
        
        if profile and profile.id_company:
            company_id = profile.id_company
            
            # Stap 2: Haal alle projecten op voor die company_id
            # Sorteer ze op naam (project_name.asc()) voor een mooie lijst
            user_projects = Project.query.filter_by(id_company=company_id).order_by(Project.project_name.asc()).all()
            
    # Zorgt dat {{ user_projects }} overal beschikbaar is
    return dict(user_projects=user_projects)