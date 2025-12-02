from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
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
)
import uuid  # mag blijven staan als je het later nodig hebt
from flask import (
    send_file,
)  # send_file laat je een bestand terugsturen als HTTP response (voor PDF knop)
from io import (
    BytesIO,
)  # BytesIO is een buffer in geheugen (geen fysiek bestand) (voor PDF knop)

import matplotlib

matplotlib.use("Agg")  # gebruik een non-GUI backend (belangrijk op macOS servers)
import matplotlib.pyplot as plt  # Matplotlib gebruiken we om de grafiek te tekenen (voor PDF knop)

import numpy as np  # Nodig voor array bewerkingen als u dit in een aparte file zet
import matplotlib.patches as patches

# Blueprint aanmaken
main = Blueprint("main", __name__)


# ==============================
# INDEX ROUTE
# ==============================
@main.route("/", methods=["GET"])
def index():
    # If logged in → go to dashboard
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))

    # Otherwise → show start page
    return render_template("index.html")


# ==============================
# LOGIN ROUTE
# ==============================
@main.route("/login", methods=["GET", "POST"])
def login():
    print("Login route started")
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        print(f"Login attempt received: email={email}")

        # Zoek user op email
        user = Profile.query.filter_by(email=email).first()

        # Controleer wachtwoord via Argon2
        if user and user.check_password(password):
            session["user_id"] = user.id_profile
            session["name"] = user.name
            session["role"] = user.role

            flash("Successfully logged in!", "success")
            print("Login successful")
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid email or password.", "danger")
            print("Invalid credentials")

    return render_template("login.html")


# ==============================
# REGISTER ROUTE (WORKS WITH SUPABASE STRUCTURE)
# ==============================
@main.route("/register", methods=["GET", "POST"])
def register():
    print("Register route started")

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")
        company_name = request.form.get("company_name")

        print(f"Full request.form content: {request.form}")
        print(f"Data received: {name} {email} {role} {company_name}")

        try:
            # Zoek of company bestaat
            company = db.session.execute(
                db.text(
                    """
                    SELECT * FROM public.company WHERE company_name = :company_name LIMIT 1
                """
                ),
                {"company_name": company_name},
            ).fetchone()

            if not company:
                db.session.execute(
                    db.text(
                        """
                        INSERT INTO public.company (company_name)
                        VALUES (:company_name)
                    """
                    ),
                    {"company_name": company_name},
                )
                db.session.commit()

                company = db.session.execute(
                    db.text(
                        """
                        SELECT * FROM public.company WHERE company_name = :company_name LIMIT 1
                    """
                    ),
                    {"company_name": company_name},
                ).fetchone()

            # Maak nieuw Profile object via ORM
            new_user = Profile(
                name=name, email=email, role=role, id_company=company.id_company
            )
            new_user.set_password(password)  # Argon2 hash wordt hier gezet

            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! You can now log in.", "success")
            print("Registration successful")
            return redirect(url_for("main.login"))

        except Exception as e:
            db.session.rollback()
            print(f"ERROR during registration: {e}")
            flash("An error occurred during registration.", "danger")

    return render_template("register.html")


# ==============================
# DASHBOARD ROUTE
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
# LOGOUT ROUTE
# ==============================
@main.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


# ==============================
# PROFILE PAGE ROUTE
# ==============================
@main.route("/profile")
def profile():
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    # Get current user
    user = Profile.query.get(session["user_id"])
    company = Company.query.get(user.id_company)

    return render_template(
        "profile.html",
        name=user.name,
        email=user.email,
        company=company.company_name,
        role=user.role,
    )


# New route add_feature
@main.route("/projects/<int:project_id>/add-feature", methods=["GET", "POST"])
def add_feature(project_id):
    # Require login
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    # Role control: Founder OR PM
    if session.get("role") not in ["founder", "PM"]:
        flash("Only Founders or PMs can add new features.", "danger")
        return redirect(url_for("main.projects"))

    # Haal project en company op
    project = Project.query.get_or_404(project_id)
    company = project.company

    if request.method == "POST":
        # Helper to convert safely to int
        # routes.py (Gecorrigeerde helperfunctie, noem hem to_numeric of to_int)

        def to_numeric(
            field_name, is_float=False
        ):  # <-- Zorg dat dit argument aanwezig is!
            raw = request.form.get(field_name, "").strip()
            if not raw:
                return None
            try:
                return float(raw) if is_float else int(raw)
            except ValueError:
                return None  # Zorgt ervoor dat ongeldige input None (NULL) wordt

        # Basic info
        name_feature = request.form.get("name_feature", "").strip()
        description = request.form.get("description", "").strip()

        # ROI fields
        extra_revenue = to_numeric("extra_revenue")  # Was 'revenue', nu 'extra_revenue'
        churn_reduction = to_numeric("churn_reduction")  # Veld toevoegen voor Churn
        cost_savings = to_numeric("cost_savings")
        investment_hours = to_numeric("investment_hours")
        opex_hours = to_numeric("opex_hours")
        other_costs = to_numeric("other_costs")
        horizon = to_numeric("horizon")
        # roi_percent = request.form.get('roi_percent')  # readonly, string/float

        # TTV fields
        ttm_weeks = to_numeric("ttm_weeks")
        ttbv_weeks = to_numeric("ttbv_weeks")
        ttv_weeks_raw = request.form.get("ttv_weeks", "").strip()
        try:
            ttv_weeks = float(ttv_weeks_raw) if ttv_weeks_raw else None
        except ValueError:
            # Als het een lege string is, zal het al None zijn. Als het een ongeldige string is,
            # moet je misschien valideren of None retourneren.
            ttv_weeks = None

        # Confidence
        quality_score = request.form.get("quality_score")

        # Validations
        errors = []
        if not name_feature:
            errors.append("Title is required.")

        numeric_fields = {
            "Title": name_feature,  # De title check blijft
            "Extra Revenue": extra_revenue,
            "Churn Reduction": churn_reduction,
            "Cost savings": cost_savings,
            "Investment hours": investment_hours,
            "OPEX hours": opex_hours,
            "Other costs": other_costs,
            "Horizon": horizon,
            "TTM weeks": ttm_weeks,
            "TTBV weeks": ttbv_weeks,
        }
        for label, value in numeric_fields.items():
            if value is None:
                errors.append(f"{label} must be an integer.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_feature.html", project=project, company=company)

        # Create a unique ID for the feature
        new_id = str(uuid.uuid4())

        # BEREKEN ROI WAARDEN
        total_gains = (
            (extra_revenue or 0) + (churn_reduction or 0) + (cost_savings or 0)
        )
        total_costs = (investment_hours or 0) + (opex_hours or 0) + (other_costs or 0)

        # Bereken Expected Profit (Net Gains)
        expected_profit = total_gains - total_costs

        # Bereken ROI in percentage: (Netto Winst / Totale Kosten) * 100
        # Alleen berekenen als de kosten > 0 zijn om delen door nul te voorkomen
        if total_costs > 0:
            roi_percent = ((total_gains / total_costs) - 1) * 100
            # Afkappen op 2 decimalen
            roi_percent = round(roi_percent, 2)
        else:
            # Als er geen kosten zijn, is de ROI oneindig hoog; stel een hoge (of NULL) waarde in
            roi_percent = None if total_gains == 0 else 9999.0

        # BEREKEN TTV WAARDEN
        ttv_weeks = (ttm_weeks or 0) + (ttbv_weeks or 0)
        ttv_weeks = float(ttv_weeks)  # Zet om naar float voor de database

        try:
            feature = Features_ideas(
                id_feature=new_id,  # primary key
                id_company=company.id_company,
                id_project=project.id_project,
                name_feature=name_feature,
                description=description,
                extra_revenue=extra_revenue,
                churn_reduction=churn_reduction,
                cost_savings=cost_savings,
                investment_hours=investment_hours,
                opex_hours=opex_hours,
                other_costs=other_costs,
                horizon=horizon,
                expected_profit=expected_profit,  # Berekende waarde opslaan
                roi_percent=roi_percent,  # Berekende waarde opslaan
                ttm_weeks=ttm_weeks,
                ttbv_weeks=ttbv_weeks,
                ttv_weeks=ttv_weeks,  # Berekende waarde opslaan
                quality_score=quality_score,
            )
            db.session.add(feature)
            db.session.commit()

            flash("Feature saved successfully.", "success")
            return redirect(url_for("main.projects"))

        except Exception as e:
            db.session.rollback()
            print(f"Error while saving feature: {e}")
            flash("An error occurred while saving.", "danger")
            return render_template("add_feature.html", project=project, company=company)

    # GET
    return render_template("add_feature.html", project=project, company=company)


# ==============================
# VECTR CHART OVERZICHT ROUTE
# ==============================
@main.route("/projects/<int:project_id>/vectr-chart", methods=["GET"])
def vectr_chart(project_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    project = Project.query.get_or_404(project_id)

    # Beveiliging: controleer of het project van het bedrijf van de gebruiker is
    if project.id_company != user.id_company:
        flash("You are not allowed to view this chart.", "danger")
        return redirect(url_for("main.projects"))

    # Alle features ophalen die de benodigde data hebben
    features = Features_ideas.query.filter_by(id_project=project_id).all()

    # Data transformeren naar een formaat dat geschikt is voor de grafiek (JSON)
    chart_data = []
    for f in features:
        # Zorg ervoor dat we alleen features met geldige data plotten
        if (
            f.roi_percent is not None
            and f.quality_score is not None
            and f.ttv_weeks is not None
        ):
            chart_data.append(
                {
                    "name": f.name_feature,
                    # X-as: Confidence
                    "confidence": float(f.quality_score),
                    # Y-as: TtV (weeks)
                    "ttv": float(f.ttv_weeks),
                    # Grootte (Bubble Size): ROI (%)
                    "roi": float(f.roi_percent),
                    "id": f.id_feature,
                }
            )
    # Geef de data door aan de template
    return render_template("vectr_chart.html", project=project, chart_data=chart_data)


# ==============================
# VIEW FEATURES ROUTE
# ==============================
@main.route("/projects/<int:project_id>/features", methods=["GET"])
def view_features(project_id):
    # 1. Beveiliging en Gebruikersgegevens ophalen
    if "user_id" not in session:
        flash("U moet eerst inloggen.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    project = Project.query.get_or_404(project_id)
    company = Company.query.get_or_404(user.id_company)

    # Beveiliging: controleer of het project van het bedrijf van de gebruiker is
    if project.id_company != user.id_company:
        flash("U mag dit project niet bekijken.", "danger")
        return redirect(url_for("main.projects"))

    # 2. Bepaal de rol en sorteerpermissie
    user_role = session.get("role")
    can_sort = user_role == "PM"

    # 3. Parameters Bepalen op basis van de Rol
    if can_sort:
        # PM: Haal parameters uit URL, standaard op 'roi' desc
        sort_by = request.args.get("sort_by", "roi")
        direction = request.args.get("direction", "desc")
    else:
        # Andere Rollen: Forceer standaard sortering op naam/ID (niet-dynamisch)
        sort_by = "name"  # of 'id'
        direction = "asc"

    # 4. Bepaal de SQLAlchemy-kolom voor sortering

    # Standaard query om alle features voor dit project op te halen
    features_query = Features_ideas.query.filter_by(id_project=project_id)

    if sort_by == "roi":
        column = Features_ideas.roi_percent
    elif sort_by == "ttv":
        # Sorteer op TTM (Time-to-Market) als proxy voor TTV, omdat TTV berekend is
        column = Features_ideas.ttm_weeks
    elif sort_by == "confidence":
        column = Features_ideas.quality_score
    else:
        # Fallback op naam/ID
        column = Features_ideas.name_feature

    # 5. Voer de Sortering uit
    if direction == "desc":
        features = features_query.order_by(column.desc()).all()
    else:
        features = features_query.order_by(column.asc()).all()

    # 6. Template Renderen (LET OP: komma's en alle benodigde variabelen)
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
# EDIT FEATURE ROUTE
# ==============================


@main.route("/feature/<uuid:feature_id>/edit", methods=["GET", "POST"])
def edit_feature(feature_id):
    # UUID als string opslaan
    feature = Features_ideas.query.get_or_404(str(feature_id))
    project = Project.query.get_or_404(feature.id_project)
    company = Company.query.get_or_404(project.id_company)

    if request.method == "POST":
        try:
            feature.name_feature = request.form.get("name_feature")
            feature.roi_percent = float(request.form.get("roi_percent") or 0)
            feature.ttv_weeks = float(request.form.get("ttv_weeks") or 0)
            feature.quality_score = float(request.form.get("quality_score") or 0)
            feature.horizon = float(request.form.get("horizon") or 0)

            db.session.commit()
            flash("Feature updated successfully!", "success")
            return redirect(
                url_for("main.view_features", project_id=feature.id_project)
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating feature: {e}", "danger")

    return render_template(
        "edit_feature.html", feature=feature, project=project, company=company
    )


# ==============================
# DELETE FEATURE ROUTE
# ==============================


@main.route("/feature/<uuid:feature_id>/delete", methods=["POST"])
def delete_feature(feature_id):
    feature = Features_ideas.query.get_or_404(str(feature_id))
    project_id = feature.id_project
    db.session.delete(feature)
    db.session.commit()
    flash("Feature deleted successfully!", "success")
    return redirect(url_for("main.view_features", project_id=project_id))


# ==============================
# PROJECTS OVERVIEW ROUTE
# ==============================
@main.route("/projects")
def projects():
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])

    # Project + Company name via join
    projects = (
        db.session.query(Project, Company.company_name)
        .join(Company, Project.id_company == Company.id_company)
        .filter(Project.id_company == user.id_company)
        .order_by(Project.id_project.desc())
        .all()
    )

    return render_template("projects.html", projects=projects)


@main.route("/add_project", methods=["GET", "POST"])
def add_project():
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    # Role control: Founder OR PM
    if session.get("role") not in ["founder", "PM"]:
        flash(
            "Only Founders and Project Managers are allowed to add new projects.",
            "danger",
        )
        return redirect(url_for("main.projects"))

    # Get logged in user
    user = Profile.query.get(session["user_id"])
    user_company = Company.query.filter_by(id_company=user.id_company).first()

    if request.method == "POST":
        project_name = request.form.get("project_name")
        company_id = user_company.id_company  # auto fill

        new_project = Project(project_name=project_name, id_company=company_id)

        db.session.add(new_project)
        db.session.commit()

        flash("Project added successfully.", "success")
        return redirect(url_for("main.projects"))

    # ⬇️ Only pass 1 company (from user)
    return render_template("add_project.html", company=user_company)


# ==============================
# EDIT PROJECT
# ==============================
@main.route("/projects/edit/<int:project_id>", methods=["GET", "POST"])
def edit_project(project_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    project = Project.query.get_or_404(project_id)

    # Security: only projects from own company
    if project.id_company != user.id_company:
        flash("You are not allowed to edit this project.", "danger")
        return redirect(url_for("main.projects"))

    if request.method == "POST":
        new_name = request.form.get("project_name", "").strip()

        if not new_name:
            flash("Project name is required.", "danger")
            return render_template("edit_project.html", project=project)

        project.project_name = new_name
        db.session.commit()

        flash("Project updated successfully.", "success")
        return redirect(url_for("main.projects"))

    # GET
    return render_template("edit_project.html", project=project)


# ==============================
# DELETE PROJECT
# ==============================
@main.route("/projects/delete/<int:project_id>", methods=["POST"])
def delete_project(project_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    project = Project.query.get_or_404(project_id)

    # Security: only own company
    if project.id_company != user.id_company:
        flash("You are not allowed to delete this project.", "danger")
        return redirect(url_for("main.projects"))

    try:
        db.session.delete(project)
        db.session.commit()
        flash("Project deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Error while deleting project: {e}")
        flash("An error occurred while deleting the project.", "danger")

    return redirect(url_for("main.projects"))


# ==============================
# ROADMAP ROUTES
# ==============================


@main.route("/roadmap/add/<int:project_id>", methods=["GET", "POST"])
def add_roadmap(project_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    # Only founders
    if session.get("role") != "founder":
        flash("Only Founders can create roadmaps.", "danger")
        return redirect(url_for("main.projects"))

    user = Profile.query.get(session["user_id"])
    project = Project.query.get_or_404(project_id)

    # Must belong to same company
    if project.id_company != user.id_company:
        flash("Not allowed.", "danger")
        return redirect(url_for("main.projects"))

    # MAX 1 ROADMAP FILTER
    existing = Roadmap.query.filter_by(id_project=project_id).first()
    if existing:
        flash("This project already has a roadmap.", "danger")
        return redirect(url_for("main.roadmap_overview", project_id=project_id))

    if request.method == "POST":
        start_quarter = request.form.get("start_quarter")
        end_quarter = request.form.get("end_quarter")
        team_size = request.form.get("team_size")
        sprint_capacity = request.form.get("sprint_capacity")
        budget_allocation = request.form.get("budget_allocation")

        roadmap = Roadmap(
            id_project=project_id,
            start_quarter=start_quarter,
            end_quarter=end_quarter,
            team_size=int(team_size),
            sprint_capacity=int(sprint_capacity),
            budget_allocation=int(budget_allocation),
        )

        db.session.add(roadmap)
        db.session.commit()

        flash("Roadmap created successfully!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=project_id))

    return render_template("add_roadmap.html", project=project)


@main.route("/roadmap/<int:project_id>")
def roadmap_overview(project_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    project = Project.query.get_or_404(project_id)

    # Check company ownership
    if project.id_company != user.id_company:
        flash("You are not allowed to view this roadmap.", "danger")
        return redirect(url_for("main.projects"))

    # Alle roadmaps van dit project ophalen, en SORTEER ZE:
    # Dit sorteert op de string, wat werkt als het format "Qx YYYY" is.
    roadmaps = (
        Roadmap.query.filter_by(id_project=project_id)
        .order_by(Roadmap.start_quarter.asc())
        .all()
    )
    # Binnen elke roadmap moeten we ook de milestones sorteren (bijv. op start_date)

    for roadmap in roadmaps:
        # Sorteer milestones op start_date binnen elke roadmap
        roadmap.milestones.sort(
            key=lambda m: m.start_date if m.start_date else datetime.date.max
        )

    return render_template(
        "roadmap_overview.html", project=project, roadmaps=roadmaps  # Nu gesorteerd
    )


@main.route("/roadmap/edit/<int:roadmap_id>", methods=["GET", "POST"])
def edit_roadmap(roadmap_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    # Only founders may edit
    if session.get("role") != "founder":
        flash("Only Founders can edit roadmaps.", "danger")
        return redirect(url_for("main.projects"))

    roadmap = Roadmap.query.get_or_404(roadmap_id)
    project = Project.query.get_or_404(roadmap.id_project)
    user = Profile.query.get(session["user_id"])

    # Must belong to same company
    if project.id_company != user.id_company:
        flash("You are not allowed to edit this roadmap.", "danger")
        return redirect(url_for("main.projects"))

    # POST → update values
    if request.method == "POST":

        def to_int(value):
            try:
                return int(float(value))
            except:
                return None

        roadmap.start_quarter = request.form.get("start_quarter")
        roadmap.end_quarter = request.form.get("end_quarter")
        roadmap.team_size = to_int(request.form.get("team_size"))
        roadmap.sprint_capacity = to_int(request.form.get("sprint_capacity"))
        roadmap.budget_allocation = to_int(request.form.get("budget_allocation"))

        db.session.commit()

        flash("Roadmap updated successfully!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=project.id_project))

    # GET → show form
    return render_template("edit_roadmap.html", roadmap=roadmap, project=project)


# ==============================
# MILESTONES ROUTES
# ==============================
@main.route("/milestone/add/<int:roadmap_id>", methods=["GET", "POST"])
def add_milestone(roadmap_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    roadmap = Roadmap.query.get_or_404(roadmap_id)

    # Only founders can add
    if user.role != "founder":
        flash("Only founders can add milestones.", "danger")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    if request.method == "POST":
        name = request.form.get("name")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        goal = request.form.get("goal")
        status = request.form.get("status")

        milestone = Milestone(
            id_roadmap=roadmap_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            goal=goal,
            status=status,
        )

        db.session.add(milestone)
        db.session.commit()
        flash("Milestone added!", "success")

        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    return render_template("add_milestone.html", roadmap=roadmap)


@main.route("/milestone/edit/<int:milestone_id>", methods=["GET", "POST"])
def edit_milestone(milestone_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    milestone = Milestone.query.get_or_404(milestone_id)
    roadmap = Roadmap.query.get_or_404(milestone.id_roadmap)

    if user.role != "founder":
        flash("Only founders can edit milestones.", "danger")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    if request.method == "POST":
        milestone.name = request.form.get("name")
        milestone.start_date = request.form.get("start_date")
        milestone.end_date = request.form.get("end_date")
        milestone.goal = request.form.get("goal")
        milestone.status = request.form.get("status")

        db.session.commit()
        flash("Milestone updated!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    return render_template("edit_milestone.html", milestone=milestone)


@main.route("/milestone/delete/<int:milestone_id>", methods=["POST"])
def delete_milestone(milestone_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    milestone = Milestone.query.get_or_404(milestone_id)
    roadmap = Roadmap.query.get_or_404(milestone.id_roadmap)

    if user.role != "founder":
        flash("Only founders can delete milestones.", "danger")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    db.session.delete(milestone)
    db.session.commit()
    flash("Milestone deleted!", "success")

    return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))


@main.route("/feature/<feature_id>/add-evidence", methods=["GET", "POST"])
def add_evidence(feature_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    feature = Features_ideas.query.get_or_404(feature_id)

    if feature.id_company != user.id_company:
        flash("Not allowed.", "danger")
        return redirect(url_for("main.projects"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        type_select = request.form.get("type_select", "").strip()
        custom_type = request.form.get("custom_type", "").strip()
        source = request.form.get("source", "").strip()
        description = request.form.get("description", "").strip()
        attachment_url = request.form.get("attachment_url", "").strip()
        impact_raw = request.form.get("confidence_impact", "").strip()

        # Type logic
        final_type = (
            custom_type if (type_select == "Other" and custom_type) else type_select
        )

        # Impact
        try:
            impact = float(impact_raw)
        except:
            impact = 0.0

        ev = Evidence(
            id_company=user.id_company,
            id_feature=feature_id,
            title=title,
            type=final_type,
            source=source,
            description=description,
            attachment_url=attachment_url,
            confidence_impact=impact,
        )

        # CONFIDENCE UP
        feature.quality_score = (feature.quality_score or 0) + impact

        db.session.add(ev)
        db.session.commit()

        flash("Evidence added!", "success")
        return redirect(url_for("main.view_evidence", feature_id=feature_id))

    return render_template("add_evidence.html", feature=feature)


@main.route("/feature/<feature_id>/evidence")
def view_evidence(feature_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    feature = Features_ideas.query.get_or_404(feature_id)

    evidence_list = Evidence.query.filter_by(id_feature=feature_id).all()

    return render_template(
        "view_evidence.html", feature=feature, evidence_list=evidence_list
    )


@main.route("/evidence/<int:evidence_id>/delete", methods=["POST"])
def delete_evidence(evidence_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    ev = Evidence.query.get_or_404(evidence_id)
    feature = Features_ideas.query.get_or_404(ev.id_feature)

    # CONFIDENCE DOWN
    feature.quality_score = (feature.quality_score or 0) - (ev.confidence_impact or 0)

    db.session.delete(ev)
    db.session.commit()

    flash("Evidence deleted!", "success")
    return redirect(url_for("main.view_evidence", feature_id=feature.id_feature))


@main.route("/evidence/<int:evidence_id>/edit", methods=["GET", "POST"])
def edit_evidence(evidence_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    ev = Evidence.query.get_or_404(evidence_id)
    feature = Features_ideas.query.get_or_404(ev.id_feature)

    if ev.id_company != user.id_company:
        flash("Not allowed.", "danger")
        return redirect(url_for("main.projects"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        type_select = request.form.get("type_select", "").strip()
        custom_type = request.form.get("custom_type", "").strip()
        source = request.form.get("source", "").strip()
        description = request.form.get("description", "").strip()
        attachment_url = request.form.get("attachment_url", "").strip()
        impact_raw = request.form.get("confidence_impact", "").strip()

        # Determine type
        final_type = (
            custom_type if (type_select == "Other" and custom_type) else type_select
        )

        # Convert impact
        try:
            new_impact = float(impact_raw)
        except ValueError:
            new_impact = 0.0

        old_impact = ev.confidence_impact or 0.0
        old_conf = feature.quality_score or 0.0

        # NEW CONFIDENCE
        feature.quality_score = old_conf - old_impact + new_impact

        # Update evidence data
        ev.title = title
        ev.type = final_type
        ev.source = source
        ev.description = description
        ev.attachment_url = attachment_url
        ev.confidence_impact = new_impact

        db.session.commit()
        flash("Evidence updated!", "success")
        return redirect(url_for("main.view_evidence", feature_id=feature.id_feature))

    return render_template("edit_evidence.html", evidence=ev, feature=feature)


# ====================================================
# PDF knop ROUTE (Aangepast voor 6-Zones VECTR)
# ====================================================
@main.route("/projects/<int:project_id>/vectr-chart/pdf")
def vectr_chart_pdf(project_id):
    if "user_id" not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for("main.login"))

    user = Profile.query.get(session["user_id"])
    project = Project.query.get_or_404(project_id)
    if project.id_company != user.id_company:
        flash("You are not allowed to view this chart.", "danger")
        return redirect(url_for("main.projects"))

    features = Features_ideas.query.filter_by(id_project=project_id).all()

    # --- 1. Definieer de VECTR-grenzen ---
    CONF_MIN, CONF_MAX = 0.0, 10.0
    CONF_LOW_THRESHOLD = 1.0
    CONF_MID_HIGH_THRESHOLD = 7.0

    TTV_MIN, TTV_MAX = 0.0, 10.0
    TTV_SLOW_THRESHOLD = 5.0
    TTV_MID_THRESHOLD = 7.0

    # --- 2. Matplotlib Setup ---
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(CONF_MIN, CONF_MAX)
    ax.set_ylim(TTV_MIN, TTV_MAX)

    # --- 3. Zones ---
    zones = [
        {"color": (0/255, 150/255, 0/255, 0.25), "x": CONF_MID_HIGH_THRESHOLD, "y": TTV_MID_THRESHOLD,
         "w": CONF_MAX - CONF_MID_HIGH_THRESHOLD, "h": TTV_MAX - TTV_MID_THRESHOLD},
        {"color": (144/255, 238/255, 144/255, 0.25), "x": CONF_MID_HIGH_THRESHOLD, "y": TTV_SLOW_THRESHOLD,
         "w": CONF_MAX - CONF_MID_HIGH_THRESHOLD, "h": TTV_MID_THRESHOLD - TTV_SLOW_THRESHOLD},
        {"color": (255/255, 165/255, 0/255, 0.25), "x": CONF_MID_HIGH_THRESHOLD, "y": TTV_MIN,
         "w": CONF_MAX - CONF_MID_HIGH_THRESHOLD, "h": TTV_SLOW_THRESHOLD - TTV_MIN},
        {"color": (255/255, 0/255, 0/255, 0.25), "x": CONF_MIN, "y": TTV_SLOW_THRESHOLD,
         "w": CONF_LOW_THRESHOLD - CONF_MIN, "h": TTV_MAX - TTV_SLOW_THRESHOLD},
        {"color": (255/255, 140/255, 0/255, 0.25), "x": CONF_LOW_THRESHOLD, "y": TTV_SLOW_THRESHOLD,
         "w": CONF_MID_HIGH_THRESHOLD - CONF_LOW_THRESHOLD, "h": TTV_MAX - TTV_SLOW_THRESHOLD},
        {"color": (255/255, 0/255, 0/255, 0.25), "x": CONF_MIN, "y": TTV_MIN,
         "w": CONF_MID_HIGH_THRESHOLD - CONF_MIN, "h": TTV_SLOW_THRESHOLD - TTV_MIN},
    ]

    for zone in zones:
        rect = patches.Rectangle(
            (zone["x"], zone["y"]),
            zone["w"], zone["h"],
            facecolor=zone["color"],
            edgecolor=(0, 0, 0, 0.4),
            linewidth=0.5,
        )
        ax.add_patch(rect)

    # --- 4. Zone kleur logica ---
    def get_zone_color_mpl(confidence, ttv):
        x_low = CONF_LOW_THRESHOLD
        x_high = CONF_MID_HIGH_THRESHOLD
        y_slow = TTV_SLOW_THRESHOLD
        y_fast = TTV_MID_THRESHOLD

        if confidence >= x_high:
            if ttv >= y_fast:
                return (0/255, 150/255, 0/255, 1)      # Donkergroen
            elif y_slow <= ttv < y_fast:
                return (144/255, 238/255, 144/255, 1)  # Lichtgroen
            else:
                return (255/255, 165/255, 0/255, 1)    # Licht Oranje
        else:
            if ttv < y_slow:
                return (255/255, 0/255, 0/255, 1)      # Rood (Zone 1)
            elif confidence < x_low:
                return (255/255, 0/255, 0/255, 1)      # Rood (Zone 3)
            else:
                return (255/255, 140/255, 0/255, 1)    # Donker Oranje

    # --- 5. Features plotten ---
    scatter_x, scatter_y, scatter_s, scatter_c, scatter_labels = [], [], [], [], []
    for f in features:
        if f.roi_percent is not None and f.quality_score is not None and f.ttv_weeks is not None:
            conf = float(f.quality_score)
            ttv_weeks = float(f.ttv_weeks)
            roiValue = float(f.roi_percent)
            size_mpl_area = max(50, min(2000, (max(0, roiValue) * 15)))
            color = get_zone_color_mpl(conf, ttv_weeks)

            scatter_x.append(conf)
            scatter_y.append(ttv_weeks)
            scatter_s.append(size_mpl_area)
            scatter_c.append(color)
            scatter_labels.append(f.name_feature)

    scatter = ax.scatter(
        scatter_x, scatter_y,
        s=scatter_s, c=scatter_c,
        edgecolors="black", linewidths=1.0, alpha=0.8
    )

    # --- 6. Labels ---
    ax.set_xlabel("Confidence (Quality of Evidence - Hoger is Beter)")
    ax.set_ylabel("Time-to-Value (TtV) in Weken (Lager is Beter)")
    ax.set_title(f"VECTR Prioritization Chart for {project.project_name}", fontsize=14)

    ax.text(CONF_LOW_THRESHOLD, TTV_MAX + 0.5, "Low", ha="left", fontsize=10, color="gray")
    ax.text(CONF_MID_HIGH_THRESHOLD + 1.0, TTV_MAX + 0.5, "High", ha="left", fontsize=10, color="gray")
    ax.text(CONF_MIN - 0.5, TTV_MAX - 1.0, "Fast", va="center", fontsize=10, color="gray", rotation=90)
    ax.text(CONF_MIN - 0.5, TTV_MIN + 1.0, "Slow", va="center", fontsize=10, color="gray", rotation=90)

    for i, label in enumerate(scatter_labels):
        ax.annotate(label, (scatter_x[i], scatter_y[i]),
                    textcoords="offset points", xytext=(5, -5),
                    ha="left", fontsize=7)

    # --- 7. Exporteren naar PDF ---
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


# =============================
# DECISION ROUTE
# ============================
@main.route("/feature/decide/<string:feature_id>", methods=["GET", "POST"])
def make_decision(feature_id):
    feature = Features_ideas.query.get_or_404(feature_id)

    if request.method == "POST":
        decision_type = reques.form.get("decision_type")
        reasoning = request.form.get("reasoning")

        company_id = feature.id_company

        new_decision = Decision(
            id_feature=feature.id_company,
            id_company=company_id,
            decision_type=decision_type,
            reasoning=reasoning,
        )
        db.session.add(new_decision)
        db.session.commit()

        return redirect(url_for("ùain.view_decision", feature_id=feature_id))

    return render_template("make_decision.html", feature=feature)


# --- Route voor 'View Decision' ---
@main.route("/feature/<string:feature_id>")
def view_decision(feature_id):
    feature = Features_ideas.query.get_or_404(feature_id)
    decision = feature.decision
    return render_template("view_decision.html", feature=feature, decision=decision)
