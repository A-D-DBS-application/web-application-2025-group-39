import matplotlib
matplotlib.use("Agg") 
import uuid, datetime
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, send_file, Response
from sqlalchemy.orm import joinedload
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from app import db
from app.models import Profile, Company, Project, Features_ideas, Roadmap, Milestone, Evidence, Decision, ProjectChatMessage, CONFIDENCE_LEVELS
from app.constants import CONF_MIN, CONF_LOW_THRESHOLD, CONF_MID_HIGH_THRESHOLD, CONF_MAX, TTV_MIN, TTV_SLOW_THRESHOLD, TTV_MID_THRESHOLD, TTV_MAX
from app.utils.calculations import calc_roi, calc_ttv, to_numeric, calculate_feature_cost
from app.utils.form_helpers import prepare_vectr_chart_data, require_login, require_role, require_company_ownership, parse_project_form, parse_feature_form, parse_roadmap_form, parse_milestone_form, parse_evidence_form, recompute_feature_confidence
from app.utils.knapsack_optimizer import optimize_roadmap

# Blueprint
main = Blueprint("main", __name__)

#helper om te controleren of gebruiker zaken mag doen.
def require_editor_access(): 
    # 1. Login check
    user = require_login()
    if not isinstance(user, Profile):
        return user                                                 # Retourneert direct de redirect response

    # 2. Role check (Founder EN PM)
    role_redirect = require_role(["Founder", "PM"], user)
    if role_redirect:
        return role_redirect                                        # Retourneert direct de redirect response
        
    return user
# ==============================
# INDEX
# ==============================
@main.route("/", methods=["GET"])                                   # Toon de landingspagina of, indien ingelogd, ga direct naar het dashboard.
def index():
    if "user_id" in session:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")                            # Toon de index pagina


# ==============================
# LOGIN, REGISTER, LOGOUT
# ==============================
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").lower().strip()
        password = request.form.get("password") 
        
        user = Profile.query.filter_by(email=email).first()         #zoek gebruiker op basis van email
        
        #controleer of gebruiker bestaat
        if user and user.check_password(password):                  #controleer of wachtwoord overeenkomt
            session["user_id"] = user.id_profile                    # Sla essentiële info op in de sessie             
            session["name"] = user.name
            session["role"] = user.role
            flash("Successfully logged in!", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid email or password.", "danger")               # Foutmelding bij incorrecte gegevens

    return render_template("login.html")                            # Toon het inlogformulier

@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        #haal de gegevens op 
        name = request.form.get("name")
        email = (request.form.get("email") or "").lower().strip()    # email adress lower en strippen, zodat als gebruiker met hoofdletter typt het nog steeds juist is 
        password = request.form.get("password")
        role = request.form.get("role")
        company_name = request.form.get("company_name")

        if not all([name, email, password, role, company_name]):
            flash("All fields are required.", "danger")
            return render_template("register.html")
        
        #controleer of de gebruiker al bestaat op basis van email 
        if Profile.query.filter((Profile.email == email)).first():
            flash("This e-mail address is already registered.", "danger") 
            return redirect(url_for('main.register'))

        try:
            #Vind of maak bedrijf aan
            company = Company.query.filter_by(company_name=company_name).first()

            #maak nieuw bedrijf aan
            if not company:
                new_company = Company(company_name=company_name)
                db.session.add(new_company)
                db.session.commit()
                company = new_company  # Gebruik het nieuwe ORM-object
            #maak nieuwe gebruiker aan
            new_user = Profile(
                name=name,
                email=email,
                role=role,
                id_company=company.id_company,
            )
            new_user.set_password(password)
            #voeg gebruiker toe aan databaase
            db.session.add(new_user)
            db.session.commit()

            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for("main.login"))

        except Exception as e:
            db.session.rollback()
            print(f"Registration error: {e}")
            flash("An error occurred during registration.", "danger")
    #bij een GET-verzoek toon het registratieformulier
    return render_template("register.html")

@main.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))


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
# ABOUT VECTR
# ==============================
@main.route("/about-vectr") 
def about_vectr():
    """Renders the About VECTR information page."""
    # Deze pagina vereist geen specifieke database-informatie
    return render_template(
        "about_vectr.html",
    )



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
# EDIT PROFILE
# ==============================

@main.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    user = require_login()
    if not isinstance(user, Profile):
        return user  # Redirect naar login

    # Haal de huidige bedrijfsnaam op voor de template
    current_company = Company.query.get(user.id_company)
    current_company_name = current_company.company_name if current_company else ""

    # (Aanname: u heeft de lijst met rollen gedefinieerd in app.models of app.constants)
    # Vervang '...' door de daadwerkelijke variabele, bijv. AVAILABLE_ROLES
    AVAILABLE_ROLES = ["User", "Founder", "PM"] 
    
    if request.method == "POST":
        try:
            # 1. Gegevens ophalen
            name = (request.form.get("name") or "").strip()
            email = (request.form.get("email") or "").lower().strip()
            role = request.form.get("role")
            company_name = (request.form.get("company_name") or "").strip()
            password = request.form.get("password")

            # 2. Basisvalidatie
            if not all([name, email, role, company_name]):
                flash("Alle velden zijn verplicht.", "danger")
                return render_template("edit_profile.html", user=user, company_name=current_company_name, available_roles=AVAILABLE_ROLES)

            # 3. Controleer op e-mail duplicatie (uitgezonderd de huidige gebruiker)
            if Profile.query.filter(Profile.email == email, Profile.id_profile != user.id_profile).first():
                flash("Dit e-mailadres is al in gebruik.", "danger")
                return render_template("edit_profile.html", user=user, company_name=current_company_name, available_roles=AVAILABLE_ROLES)

            # 4. Bedrijf Logica: Vind of Maak aan (alleen als de naam is gewijzigd)
            if company_name != current_company_name:
                company = Company.query.filter_by(company_name=company_name).first()
                if not company:
                    # Nieuw bedrijf aanmaken
                    new_company = Company(company_name=company_name)
                    db.session.add(new_company)
                    db.session.flush() # Zorg dat ID beschikbaar is voor user
                    company = new_company
                
                # Update de bedrijfs-ID van de gebruiker
                user.id_company = company.id_company

            # 5. Profielgegevens bijwerken
            user.name = name
            user.email = email
            user.role = role
            
            if password:
                user.set_password(password)

            # 6. Database opslaan en sessie bijwerken
            db.session.commit()
            session["name"] = user.name
            session["role"] = user.role # Update de rol in de sessie
            
            flash("Profiel succesvol bijgewerkt.", "success")
            return redirect(url_for("main.profile"))

        except Exception as e:
            db.session.rollback()
            print(f"Fout bij het bewerken van het profiel: {e}")
            flash("Er is een onverwachte fout opgetreden bij het opslaan van de wijzigingen.", "danger")
            return render_template("edit_profile.html", user=user, company_name=current_company_name, available_roles=AVAILABLE_ROLES)

    # GET verzoek: Toon het edit-formulier
    return render_template(
        "edit_profile.html", 
        user=user, 
        company_name=current_company_name, 
        available_roles=AVAILABLE_ROLES # Geef de lijst met rollen mee
    )
# ==============================
# DELETE PROFILE
# ==============================

@main.route("/profile/delete", methods=["POST"])
def delete_profile():
    # 1. Authenticatie check
    user = require_login()
    if not isinstance(user, Profile):
        return user  # Redirect naar login
        
    try:
        # 2. Verwijder de gebruiker uit de database
        db.session.delete(user)
        db.session.commit()
        
        # 3. Ruim de sessie op
        session.clear()

        flash("Uw profiel is succesvol verwijderd. Tot ziens!", "success")
        return redirect(url_for("main.index"))  # Stuur terug naar de landingspagina

    except Exception as e:
        db.session.rollback()
        print(f"Fout bij het verwijderen van het profiel: {e}")
        flash("Er is een fout opgetreden bij het verwijderen van het profiel.", "danger")
        return redirect(url_for("main.profile"))

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
    user = require_editor_access()
    if not isinstance(user, Profile):
        return user                                                             # Afgevangen door helper: retourneert redirect/error

    user_company = Company.query.get(user.id_company)

    if request.method == "POST":
        data, errors = parse_project_form(request.form)                          # Helper-functie valideert en parseert het formulier
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_project.html", company=user_company)

        new_project = Project(
            project_name=data["project_name"],
            id_company=user_company.id_company,
            ttm_low_limit=data["ttm_low_limit"],
            ttm_high_limit=data["ttm_high_limit"],
            ttbv_low_limit=data["ttbv_low_limit"],
            ttbv_high_limit=data["ttbv_high_limit"],
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
    user = require_editor_access()
    if not isinstance(user, Profile):
        return user                                                                 # Afgevangen door helper: retourneert redirect/error

    project = Project.query.get_or_404(project_id)

    # De volgende stap moet in deze route blijven, omdat deze projectspecifiek is.
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
        project.ttm_low_limit = data["ttm_low_limit"]
        project.ttm_high_limit = data["ttm_high_limit"]
        project.ttbv_low_limit = data["ttbv_low_limit"]
        project.ttbv_high_limit = data["ttbv_high_limit"]
        
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

    # Alleen Founders mogen verwijderen
    role_redirect = require_role(["Founder"], user)
    if role_redirect:
        return role_redirect
    
    project = Project.query.get_or_404(project_id)
    
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
    user = require_editor_access()
    
    if not isinstance(user, Profile):
        return user
    
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

    # Company ophalen via project-relatie (aangenomen dat project.company bestaat)
    company = project.company

    user_role = session.get("role")
    can_sort = user_role == "PM"                                                # Alleen PM's mogen sorteren op berekende scores

    if can_sort:
        sort_by = request.args.get("sort_by", "roi")
        direction = request.args.get("direction", "desc")                       # Haal de sorteerrichting op uit de URL
    else:
        sort_by = "name"                                                        # Als GEEN PM: De gebruiker mag de sorteerparameters niet bepalen.
        direction = "asc"                                                       # De sortering wordt vastgezet op een neutrale, standaardkolom (naam) in oplopende volgorde.


    features_query = Features_ideas.query.filter_by(id_project=project_id).options(joinedload(Features_ideas.decisions)) # Laadt de decisions voor elke feature
        
    if sort_by == "roi":
        column = Features_ideas.roi_percent                                     # Sorteren op de berekende ROI in percentage
    elif sort_by == "ttv":
        column = Features_ideas.ttm_weeks
    elif sort_by == "confidence":
        column = Features_ideas.quality_score
    else:
        column = Features_ideas.name_feature

    if direction == "desc":
        features = features_query.order_by(column.desc()).all()                 # Order By DESC (Descending): Hoogste waarde eerst
    else:
        features = features_query.order_by(column.asc()).all()                  # Order By ASC (Ascending): Laagste waarde eerst


    # Compute VECTR score
    for f in features:
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        vectr_score = ttv_weeks * (roi_percent/100) * confidence_score
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
    role_redirect = require_role(["Founder", "PM"], user)
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
    user = require_login()                      # Controleer of gebruiker ingelogd is; anders redirect
    if not isinstance(user, Profile):           # require_login() kan Response teruggeven → direct teruggeven
        return user

    feature = Features_ideas.query.get_or_404(str(feature_id))  # Haalt feature op; 404 als niet gevonden
    project = Project.query.get_or_404(feature.id_project)      # Haalt project op waar feature toe behoort

    company_redirect = require_company_ownership(project.id_company, user)  # Check dat user van juiste company is
    if company_redirect:
        return company_redirect
    
    # Only founder/PM + ownership
    role_redirect = require_role(["Founder"], user)
    if role_redirect:
        return role_redirect                                    # Geeft redirect als ongeldig

    project_id = feature.id_project               # Project ID opslaan zodat we na delete kunnen redirecten
    db.session.delete(feature)                    # Feature verwijderen uit database
    db.session.commit()                           # Veranderingen opslaan
    flash("Feature deleted successfully!", "success")  # Succesbericht tonen
    return redirect(url_for("main.view_features", project_id=project_id))  # Terug naar feature-lijst



# ==============================
# VECTR CHART (WEB)
# ==============================
@main.route("/projects/<int:project_id>/vectr-chart", methods=["GET"])
def vectr_chart(project_id):
    user = require_login()                    # Check login
    if not isinstance(user, Profile):         # Als niet ingelogd → redirect
        return user

    project = Project.query.get_or_404(project_id)  # Haal project op of toon 404
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect               # Blokkeer toegang tot projecten van andere companies

    features = Features_ideas.query.filter_by(id_project=project_id).all()   # Alle features voor dit project ophalen

    # De volledige berekening wordt uitgevoerd in een aparte helperfunctie voor overzichtelijkheid
    chart_data = prepare_vectr_chart_data(project, features)

    return render_template(
        "vectr_chart.html",                   # Template dat de grafiek tekent
        project=project,                      # Project-info naar de template sturen
        chart_data=chart_data                 # Computed chart data naar template
    )



# ==============================
# ADD ROADMAP
# ==============================
@main.route("/roadmap/add/<int:project_id>", methods=["GET", "POST"])
def add_roadmap(project_id):
    user = require_login()                     # Eerst check: is de gebruiker ingelogd?
    if not isinstance(user, Profile):
        return user                            # require_login kan Response teruggeven (redirect)

    # Founders and PM's roadmaps maken
    role_redirect = require_role(["Founder", "PM"], user)  # Enkel founders mogen roadmaps maken
    if role_redirect:
        return role_redirect

    project = Project.query.get_or_404(project_id)   # Project ophalen (404 als niet gevonden)
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect                       # Users mogen alleen roadmaps maken in eigen company

    # MAX 1 ROADMAP PER PROJECT
    existing = Roadmap.query.filter_by(id_project=project_id).first()
    if existing:                                      # Als er al een roadmap bestaat
        flash("This project already has a roadmap.", "danger")
        return redirect(url_for("main.roadmap_overview", project_id=project_id))

    if request.method == "POST":                      # Wanneer formulier verstuurd is:
        data, errors = parse_roadmap_form(request.form)   # Validatie via helper
        if errors:                                     # Validatiefouten → opnieuw formulier tonen
            for e in errors:
                flash(e, "danger")
            return render_template("add_roadmap.html", project=project)

        roadmap = Roadmap(id_project=project_id, **data)  # Nieuwe Roadmap aanmaken
        db.session.add(roadmap)                      # Toevoegen aan DB
        db.session.commit()                          # Opslaan

        flash("Roadmap created successfully!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=project_id))

    # GET → pagina tonen
    return render_template("add_roadmap.html", project=project)

# ==============================
# ROADMAP OVERVIEW
# ==============================

@main.route("/roadmap/<int:project_id>")
def roadmap_overview(project_id):
    user = require_login()                          # Login check
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)   # Project ophalen
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect                     # Geen toegang buiten eigen bedrijf

    # Roadmaps sorted by start_roadmap (string sort works for "Qn YYYY")
    roadmaps = (
        Roadmap.query.filter_by(id_project=project_id)
        .order_by(Roadmap.start_roadmap.asc())      # Roadmaps chronologisch sorteren
        .all()
    )

    # Milestones binnen roadmaps sorteren op startdatum
    for roadmap in roadmaps:
        roadmap.milestones.sort(
            key=lambda m: m.start_date if m.start_date else datetime.date.max
        )                                           # Milestones zonder datum helemaal onderaan

    return render_template(
        "roadmap_overview.html",
        project=project,
        roadmaps=roadmaps,
    )

# ==============================
# EDIT ROADMAP
# ==============================

@main.route("/roadmap/edit/<int:roadmap_id>", methods=["GET", "POST"])
def edit_roadmap(roadmap_id):
    user = require_login()                           # Login check
    if not isinstance(user, Profile):
        return user

    # Founders and PM's mogen editen
    role_redirect = require_role(["Founder", "PM"], user)  # Enkel Founder mag roadmap aanpassen
    if role_redirect:
        return role_redirect

    roadmap = Roadmap.query.get_or_404(roadmap_id)   # Roadmap ophalen
    project = Project.query.get_or_404(roadmap.id_project)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect                      # Blokkeer toegang tot andere companies

    if request.method == "POST":
        data, errors = parse_roadmap_form(request.form)   # Validatie helper
        if errors:                                       # Bij fouten → formulier opnieuw tonen
            for e in errors:
                flash(e, "danger")
            return render_template("edit_roadmap.html", roadmap=roadmap, project=project)

        # Velden aanpassen
        roadmap.start_roadmap = data["start_roadmap"]
        roadmap.end_roadmap = data["end_roadmap"]
        roadmap.team_size = data["team_size"]
        roadmap.sprint_capacity = data["sprint_capacity"]
        roadmap.budget_allocation = data["budget_allocation"]

        db.session.commit()                           # Opgeslagen wijzigingen

        flash("Roadmap updated successfully!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=project.id_project))

    # GET → formulier tonen
    return render_template("edit_roadmap.html", roadmap=roadmap, project=project)

#==============================
# KNAPSACK ALGORITME
#==============================

@main.route("/roadmap/optimize/<int:roadmap_id>", methods=["GET", "POST"])
def roadmap_optimize(roadmap_id):
    user = require_editor_access()
    if not isinstance(user, Profile):
        return user
    
    roadmap = Roadmap.query.get_or_404(roadmap_id)
    project = Project.query.get_or_404(roadmap.id_project)
    
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    # 1. Haal alle features op en bereken de VECTR-scores 
    features = Features_ideas.query.filter_by(id_project=project.id_project).all()
    # Zorg dat de VECTR score op de features is gezet vóórdat je optimize_roadmap aanroept!
    # Dit is cruciaal. Je kunt hiervoor de calculate_vectr_scores uit calculations.py gebruiken.
    # (Let op: de calculate_vectr_scores functie in calculations.py gebruikt ttv_weeks * (roi_percent/100) * confidence_score, wat een simpele formule is, maar werkt.)

    from app.utils.calculations import calculate_vectr_scores
    features = calculate_vectr_scores(features)
    
    # Standaard Alpha
    alpha = 1.0 
    
    if request.method == "POST":
        # Gebruiker kan de strategische weging (Alpha) instellen via een formulier
        alpha = to_numeric(request.form.get("alpha", 1.0))
        if not 0.0 <= alpha <= 1.0:
            flash("Alpha moet tussen 0.0 en 1.0 liggen.", "danger")
            alpha = 1.0 # fallback

    # 2. Voer het Knapzak-algoritme uit
    optimized_selection = optimize_roadmap(roadmap, features, alpha=alpha)

    # 3. Zorg dat de originele features (voor de niet-geselecteerde) ook de dichtheid hebben
    # zodat de tabel kan worden weergegeven
    all_features_data = []
    
    # We hergebruiken de logic om de density per feature te krijgen, 
    # zodat we de features kunnen sorteren in de template
    for f in features:
        # Bereken de cost_weight met de geimporteerde helper
        cost_weight = calculate_feature_cost(f)
        
        time_weight = f.investment_hours if f.investment_hours is not None else 0
        value = f.vectr_score if f.vectr_score is not None else 0
        
        # ... (de rest van de logica in de lus blijft hetzelfde)
        
        all_features_data.append({
            'feature': f,
            'is_selected': f in optimized_selection,
            # Voeg gewicht en kosten toe voor weergave in de template
            'time_weight': time_weight, 
            'cost_weight': cost_weight
        })
        
    # Sorteer de data (geselecteerde features bovenaan, daarna op VECTR-score)
    all_features_data.sort(key=lambda x: (x['is_selected'], x['feature'].vectr_score if x['feature'].vectr_score is not None else 0), reverse=True)


    return render_template(
        "roadmap_optimization_result.html",
        roadmap=roadmap,
        project=project,
        features_data=all_features_data,
        alpha=alpha,
        max_time=roadmap.sprint_capacity * roadmap.team_size, # Gebruik de berekende max
        max_cost=roadmap.budget_allocation
    )



# ==============================
# ADD MILESTONES
# ==============================

@main.route("/milestone/add/<int:roadmap_id>", methods=["GET", "POST"])
def add_milestone(roadmap_id):
    user = require_editor_access()  # Controle: enkel Founder/PM mogen milestones toevoegen.

    roadmap = Roadmap.query.get_or_404(roadmap_id)  # Haal de roadmap op; 404 bij fout.
    project = Project.query.get_or_404(roadmap.id_project)  # Project van de roadmap ophalen.

    # Check of user toegang heeft tot dit bedrijf
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect  # Blokkeert toegang als user niet van dezelfde company is.

    # Alle features van dit project ophalen
    features = Features_ideas.query.filter_by(id_project=project.id_project).all()

    # VECTR score berekenen voor sortering
    for f in features:
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5  # Default TtV waarde
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        vectr_score = ttv_weeks * (roi_percent/100) * confidence_score  # Basis VECTR-formule
        setattr(f, "vectr_score", round(vectr_score, 2))  # Dynamisch attribuut toevoegen.

    # Features sorteren op VECTR score (beste eerst)
    features = sorted(features, key=lambda x: getattr(x, "vectr_score", 0), reverse=True)

    if request.method == "POST":  # Wanneer het formulier verzonden is:
        data, errors = parse_milestone_form(request.form)  # Validatie

        if errors:
            for e in errors:
                flash(e, "danger")  # Toon alle errors bovenaan
            return render_template(
                "add_milestone.html",
                roadmap=roadmap,
                features=features,
                selected_features=request.form.getlist("features"),
            )

        # Nieuwe milestone aanmaken
        milestone = Milestone(
            id_roadmap=roadmap_id,
            name=data["name"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            goal=data["goal"],
            status=data["status"],
        )

        # 🎯 Meerdere features koppelen (via de associatietabel milestone_features)
        selected = request.form.getlist("features")  # IDs van geselecteerde features
        milestone.features = Features_ideas.query.filter(
            Features_ideas.id_feature.in_(selected)
        ).all()

        db.session.add(milestone)  # Toevoegen aan DB
        db.session.commit()        # Wijzigingen opslaan

        flash("Milestone added!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    # GET → pagina tonen
    return render_template(
        "add_milestone.html",
        roadmap=roadmap,
        features=features,
        selected_features=[],
    )

# ==============================
# EDIT MILESTONES
# ==============================


@main.route("/milestone/edit/<int:milestone_id>", methods=["GET", "POST"])
def edit_milestone(milestone_id):
    user = require_editor_access()  # PM/Founder check

    milestone = Milestone.query.get_or_404(milestone_id)  # Bestaande milestone ophalen
    roadmap = Roadmap.query.get_or_404(milestone.id_roadmap)
    project = Project.query.get_or_404(roadmap.id_project)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect  # Toegang beperken tot eigen company

    # Alle features van dit project ophalen
    features = Features_ideas.query.filter_by(id_project=project.id_project).all()

    # VECTR score berekenen (zoals bij add_milestone)
    for f in features:
        ttv_weeks = f.ttv_weeks if f.ttv_weeks is not None else 5.5
        roi_percent = f.roi_percent if f.roi_percent is not None else 0.0
        confidence_score = f.quality_score if f.quality_score is not None else 0.0
        vectr_score = ttv_weeks * (roi_percent/100) * confidence_score
        setattr(f, "vectr_score", round(vectr_score, 2))

    features = sorted(features, key=lambda x: getattr(x, "vectr_score", 0), reverse=True)

    # IDs van features die al gekoppeld zijn aan deze milestone (prefill)
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
                selected_features=request.form.getlist("features"),  # Prefill vanuit form
            )

        # Velden aanpassen
        milestone.name = data["name"]
        milestone.start_date = data["start_date"]
        milestone.end_date = data["end_date"]
        milestone.goal = data["goal"]
        milestone.status = data["status"]

        # Nieuwe selectie van features koppelen
        selected = request.form.getlist("features")
        milestone.features = Features_ideas.query.filter(
            Features_ideas.id_feature.in_(selected)
        ).all()

        db.session.commit()  # Opslaan in database

        flash("Milestone updated!", "success")
        return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))

    return render_template(
        "edit_milestone.html",
        milestone=milestone,
        features=features,
        selected_features=existing_selected,
    )

# ==============================
# DELETE MILESTONE
# ==============================

@main.route("/milestone/delete/<int:milestone_id>", methods=["POST"])
def delete_milestone(milestone_id):
    user = require_login()  # Login check
    if not isinstance(user, Profile):
        return user

    # Alleen Founders mogen verwijderen
    role_redirect = require_role(["Founder"], user)
    if role_redirect:
        return role_redirect

    milestone = Milestone.query.get_or_404(milestone_id)  # Opzoeken of 404
    roadmap = Roadmap.query.get_or_404(milestone.id_roadmap)
    project = Project.query.get_or_404(roadmap.id_project)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect  # Veiligheidscheck: mag je dit milestone wel verwijderen?

    db.session.delete(milestone)  # Milestone verwijderen
    db.session.commit()           # Permanent opslaan

    flash("Milestone deleted!", "success")
    return redirect(url_for("main.roadmap_overview", project_id=roadmap.id_project))



# ==============================
# EVIDENCE: ADD
# ==============================
@main.route("/feature/<feature_id>/add-evidence", methods=["GET", "POST"])
def add_evidence(feature_id):
    user = require_login()                     # Login check
    if not isinstance(user, Profile):
        return user

    feature = Features_ideas.query.get_or_404(feature_id)  # Feature ophalen
    project = Project.query.get_or_404(feature.id_project)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect  # Voorkomt dat users bij andere companies evidence toevoegen

    if request.method == "POST":
        data, errors = parse_evidence_form(request.form)  # Form validatie
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_evidence.html", feature=feature, CONFIDENCE_LEVELS=CONFIDENCE_LEVELS)

        old_conf = feature.quality_score or 0.0  # Bewaar oude confidence

        ev = Evidence(
            id_company=user.id_company,
            id_feature=feature_id,
            title=data["title"],
            type=data["final_type"],           # Standaard type of custom type
            source=data["source"],
            description=data["description"],
            attachment_url=data["attachment_url"],
            old_confidence=old_conf,
            new_confidence=data["new_confidence"],
        )

        db.session.add(ev)
        db.session.flush()  # Flush slaat tijdelijk ev op zodat het beschikbaar is in sessie voor de helperfunctie

        new_score = recompute_feature_confidence(feature)  # Confidence herberekenen via helper functie
        feature.quality_score = new_score if new_score is not None else old_conf

        db.session.commit()

        flash("Evidence added!", "success")
        return redirect(url_for("main.view_evidence", feature_id=feature_id))

    return render_template("add_evidence.html", feature=feature, CONFIDENCE_LEVELS=CONFIDENCE_LEVELS)



# ==============================
# EVIDENCE: LIST
# ==============================
@main.route("/feature/<feature_id>/evidence")
def view_evidence(feature_id):
    user = require_login()
    if isinstance(user, Response):  # require_login() kan redirect teruggeven
        return user

    feature = Features_ideas.query.get_or_404(feature_id)

    # Evidence oplijsten: hoogste confidence eerst
    evidence_list = (
        Evidence.query.filter_by(id_feature=feature_id)
        .order_by(Evidence.new_confidence.desc())
        .all()
    )

    # Maak dictionary: {confidence_value: label}
    CONFIDENCE_LABELS = {v: label for (v, label) in CONFIDENCE_LEVELS}

    return render_template(
        "view_evidence.html",
        feature=feature,
        evidence_list=evidence_list,
        CONFIDENCE_LABELS=CONFIDENCE_LABELS,
    )


# ==============================
# EVIDENCE: DELETE
# ==============================
@main.route("/evidence/<int:evidence_id>/delete", methods=["POST"])
def delete_evidence(evidence_id):
    user = require_login()
    if not isinstance(user, Profile):
        return user
    
    # Alleen Founders mogen verwijderen
    role_redirect = require_role(["Founder"], user)
    if role_redirect:
        return role_redirect

    ev = Evidence.query.get_or_404(evidence_id)  # Evidence ophalen
    feature = Features_ideas.query.get_or_404(ev.id_feature)
    project = Project.query.get_or_404(feature.id_project)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    fallback_old = ev.old_confidence or 0.0  # Oude waarde gebruiken als fallback

    db.session.delete(ev)
    db.session.flush()                        # Verwijderen verwerken voordat score herberekend wordt

    new_score = recompute_feature_confidence(feature)
    feature.quality_score = new_score if new_score is not None else fallback_old

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

        # Velden actualiseren
        ev.title = data["title"]
        ev.type = data["final_type"]
        ev.source = data["source"]
        ev.description = data["description"]
        ev.attachment_url = data["attachment_url"]
        ev.new_confidence = data["new_confidence"]

        db.session.flush()  # Score opnieuw kunnen berekenen

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
    # 1) Login check: gebruiker moet ingelogd zijn
    user = require_login()
    if not isinstance(user, Profile):
        return user  # Als require_login een redirect of error geeft, meteen terugsturen

    # 2) Haal project op en check company ownership
    project = Project.query.get_or_404(project_id)  # 404 als project niet bestaat
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect  # Redirect als user niet eigenaar is van company

    # 3) Haal alle features van dit project op
    features = Features_ideas.query.filter_by(id_project=project_id).all()

    # 4) Gebruik de centrale helper om de geschaalde chart data te verkrijgen
    # Deze helper (prepare_vectr_chart_data) haalt de grenzen uit het Project object.
    chart_data = prepare_vectr_chart_data(project, features) 

    # 5) Bepaal de TtV grenzen van het Project voor de schaal-berekening in de plot
    # De grens is nu de som van de project-limieten (TTM Low/High + TTBV Low/High)
    local_TTV_MIN = (project.ttm_low_limit or 0.0) + (project.ttbv_low_limit or 0.0)
    local_TTV_MAX = (project.ttm_high_limit or 10.0) + (project.ttbv_high_limit or 0.0)

    # 6) Setup matplotlib figuur
    fig, ax = plt.subplots(figsize=(10, 10))                # Maak een figuur en een as-object van 10x10 inch
    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(0.0, 10.0)

    # 7) Definieer zones (kleurvlakken op de chart)
    zones = [
        {"color": (1, 0, 0, 0.25), "x": 0.0, "y": 0.0, "w": 7.0, "h": 5.0},   # rood zone
        {"color": (1, 140/255, 0, 0.25), "x": 1.0, "y": 5.0, "w": 6.0, "h": 5.0}, # oranje zone
        {"color": (1, 0, 0, 0.25), "x": 0.0, "y": 5.0, "w": 1.0, "h": 5.0},   # rood smalle zone
        {"color": (0, 150/255, 0, 0.25), "x": 7.0, "y": 7.0, "w": 3.0, "h": 3.0}, # groen zone
        {"color": (144/255, 238/255, 144/255, 0.25), "x": 7.0, "y": 5.0, "w": 3.0, "h": 2.0}, # lichtgroen zone
        {"color": (1, 165/255, 0, 0.25), "x": 7.0, "y": 0.0, "w": 3.0, "h": 5.0}, # oranje zone
    ]

    # 8) Voeg zones toe als rechthoeken
    for z in zones:
        rect = patches.Rectangle(
            (z["x"], z["y"]),           # startpositie (linkeronderhoek)
            z["w"],                     # breedte van de rechthoek
            z["h"],                     # hoogte van de rechthoek
            facecolor=z["color"],       # vulkleur (RGBA)
            edgecolor=(0, 0, 0, 0.4),   # randkleur (zwart, transparant)
            linewidth=0.5,              # dikte van de rand
        )
        ax.add_patch(rect)              # voeg de rechthoek toe aan de grafiek

    # 9) Helperfunctie: bepaal kleur van een feature op basis van confidence + TTV
    def get_zone_color_mpl(confidence, ttv_scaled):
        x_low = CONF_LOW_THRESHOLD        # drempel voor lage confidence
        x_high = CONF_MID_HIGH_THRESHOLD  # drempel voor hoge confidence
        y_slow = TTV_SLOW_THRESHOLD       # drempel voor trage TTV
        y_fast = TTV_MID_THRESHOLD        # drempel voor snelle TTV

        # Logica: kies kleur afhankelijk van confidence en TTV
        if confidence >= x_high:
            if ttv_scaled >= y_fast:
                return (0, 150/255, 0, 1)  # groen
            elif y_slow <= ttv_scaled < y_fast:
                return (144/255, 238/255, 144/255, 1)  # lichtgroen
            else:
                return (1, 165/255, 0, 1)  # oranje
        else:
            if ttv_scaled < y_slow or confidence < x_low:
                return (1, 0, 0, 1)  # rood
            else:
                return (1, 140/255, 0, 1)  # oranje

    # 10) Verzamel scatter data (punten op de chart)
    scatter_x = []       # x-waarden: confidence waarden
    scatter_y = []       # y-waarden: TTV waarden
    scatter_s = []       # grootte van de cirkel (ROI)
    scatter_c = []       # kleur van de cirkel
    scatter_labels = []  # naam van de feature

    for item in chart_data: # Loop over de reeds geschaalde data uit de helper
        
        conf = item["confidence"]                       # confidence score
        ttv_scaled = item["ttv"]                        # geschaalde TTV (0-10)
        roi_val = item["roi"]                           # ROI waarde
        
        # De effectieve TTV (ttm_weeks + ttbv_weeks) zit in item["ttv_weeks"] indien nodig
        
        size_mpl_area = max(50, min(2000, max(0, roi_val) * 15))  # bubble size
        color = get_zone_color_mpl(conf, ttv_scaled)              # kleur bepalen via helperfunctie
        
        # Voegt data toe aan de lijsten
        scatter_x.append(conf)
        scatter_y.append(ttv_scaled)
        scatter_s.append(size_mpl_area)
        scatter_c.append(color)
        scatter_labels.append(item["name"])

    # 11) Plot scatter chart
    ax.scatter(
        scatter_x,
        scatter_y,
        s=scatter_s,        # grootte van de cirkel
        c=scatter_c,        # kleur van de cirkel
        edgecolors="black", # zwarte rand
        linewidths=1.0,
        alpha=0.8,          # transparantie
    )

    # 12) Labels en ticks (custom tekst op assen)
    ax.set_xticks([0, 1, 3, 5, 7, 8, 10])
    ax.set_xticklabels(["0", "Low", "3", "5", "7", "High", "10"])
    ax.set_yticks([0, 1, 2, 3, 5, 7, 8, 10])
    ax.set_yticklabels(["0", "1", "Slow", "3", "5", "7", "Fast", "10"])

    ax.set_xlabel("Confidence")                                             # x-as label
    ax.set_ylabel("Time-to-Value (TtV)")                                    # y-as label
    ax.set_title(f"VECTR Prioritization Chart for {project.project_name}")  # titel met projectnaam

    # 13) Annotaties (labels bij de punten)
    for i, label in enumerate(scatter_labels):
        ax.annotate(
            label,                        # tekst (feature naam)
            (scatter_x[i], scatter_y[i]), # positie van de cirkel
            textcoords="offset points",   # offset in pixels
            xytext=(5, -5),               # verschuiving van label
            ha="left",                    # horizontale uitlijning
            fontsize=7,                   # lettergrootte
        )

    # 14) Opslaan als PDF in geheugenbuffer
    plt.tight_layout()              # layout netjes maken
    buf = BytesIO()                 # buffer in geheugen (om data tijdelijk op te slaan zonder dat er iets op de schijft terecht komt) )
    plt.savefig(buf, format="pdf")  # figuur opslaan als PDF in buffer
    plt.close(fig)                  # figuur sluiten om geheugen vrij te maken
    buf.seek(0)                     # cursor terug naar begin van buffer

    # 15) Stuur PDF terug als download
    return send_file(
        buf,
        as_attachment=True,                                             # forceer download
        download_name=f"vectr_chart_{project.project_name}.pdf",        # bestandsnaam
        mimetype="application/pdf",                                     # soort bestand waarin het wordt gedownload
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
        # Save the value the template expects
        feature.decision = decision_type  
        db.session.add(feature)

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





# ==============================
# CHAT DASHBOARD (PROJECT-CHATS)
# ==============================

@main.route("/chat")
def chat_dashboard():
    """Toont chatdashboard: links projecten, rechts chat van eerste project."""
    user = require_login()
    if not isinstance(user, Profile):
        return user

    # Alle projecten van de company van de gebruiker
    projects = (
        Project.query
        .filter_by(id_company=user.id_company)
        .order_by(Project.project_name.asc())
        .all()
    )

    # Geen projecten? Terug naar dashboard
    if not projects:
        flash("No projects available for chat.", "danger")
        return redirect(url_for("main.dashboard"))

    # Standaard: eerste project in de lijst
    first_project = projects[0]

    messages = (
        ProjectChatMessage.query
        .filter_by(id_project=first_project.id_project)
        .order_by(ProjectChatMessage.timestamp.asc())
        .all()
    )

    return render_template(
        "chat_dashboard.html",
        projects=projects,
        selected_project=first_project,
        messages=messages,
        user=user,
    )


@main.route("/chat/project/<int:project_id>")
def chat_dashboard_project(project_id):
    """Zelfde layout, maar met een andere geselecteerde project-chat."""
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)

    # Company-check: user moet bij hetzelfde bedrijf horen als het project
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    # Alle projecten opnieuw ophalen voor de linker lijst
    projects = (
        Project.query
        .filter_by(id_company=user.id_company)
        .order_by(Project.project_name.asc())
        .all()
    )

    messages = (
        ProjectChatMessage.query
        .filter_by(id_project=project_id)
        .order_by(ProjectChatMessage.timestamp.asc())
        .all()
    )

    return render_template(
        "chat_dashboard.html",
        projects=projects,
        selected_project=project,
        messages=messages,
        user=user,
    )


@main.route("/chat/project/<int:project_id>/send", methods=["POST"])
def chat_dashboard_send(project_id):
    """Stuurt een nieuw bericht in de chat van een bepaald project."""
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)

    # Company-check
    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    text = request.form.get("content", "").strip()
    if not text:
        # Leeg bericht? Gewoon terug naar dezelfde chat (geen flash nodig)
        return redirect(url_for("main.chat_dashboard_project", project_id=project_id))

    # Nieuw chatbericht opslaan
    msg = ProjectChatMessage(
        id_project=project_id,
        id_profile=user.id_profile,
        content=text,
    )
    db.session.add(msg)
    db.session.commit()

    return redirect(url_for("main.chat_dashboard_project", project_id=project_id))

@main.route("/chat/project/<int:project_id>/messages")
def chat_project_messages(project_id):
    """Geeft alleen de chatberichten terug voor dynamische refresh."""
    user = require_login()
    if not isinstance(user, Profile):
        return user

    project = Project.query.get_or_404(project_id)

    company_redirect = require_company_ownership(project.id_company, user)
    if company_redirect:
        return company_redirect

    messages = (
        ProjectChatMessage.query
        .filter_by(id_project=project_id)
        .order_by(ProjectChatMessage.timestamp.asc())
        .all()
    )

    return render_template(
        "chat_messages.html",
        messages=messages,
        user=user,
    )