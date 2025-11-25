from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import db
from app.models import Profile, Company, Project, Features_ideas, Roadmap, Milestone
import uuid  # mag blijven staan als je het later nodig hebt


# Blueprint aanmaken
main = Blueprint('main', __name__)

# ==============================
# INDEX ROUTE
# ==============================
@main.route('/', methods=['GET'])
def index():
    # If logged in → go to dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    # Otherwise → show start page
    return render_template('index.html')

# ==============================
# LOGIN ROUTE
# ==============================
@main.route('/login', methods=['GET', 'POST'])
def login():
    print("🟢 Login route started")
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')

        print(f"📨 Login attempt received: name={name}, email={email}")

        # Search for user in profile with ORM
        user = Profile.query.filter_by(name=name, email=email).first()

        if user:
            session['user_id'] = user.id_profile
            session['name'] = user.name
            session['role'] = user.role

            flash("Successfully logged in!", "success")
            print("Login successful")
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid name or email.", "error")
            print("Invalid credentials")

    return render_template('login.html')


# ==============================
# REGISTER ROUTE (WORKS WITH SUPABASE STRUCTURE)
# ==============================
@main.route('/register', methods=['GET', 'POST'])
def register():
    print("Register route started")

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        company_name = request.form.get('company_name')

        print(f"Full request.form content: {request.form}")
        print(f"Data received: {name} {email} {role} {company_name}")

        try:
            # Search for company (or create) with raw SQL
            company = db.session.execute(
                db.text("""
                    SELECT * FROM public.company WHERE company_name = :company_name LIMIT 1
                """),
                {'company_name': company_name}
            ).fetchone()

            if not company:
                db.session.execute(
                    db.text("""
                        INSERT INTO public.company (company_name)
                        VALUES (:company_name)
                    """),
                    {'company_name': company_name}
                )
                db.session.commit()

                company = db.session.execute(
                    db.text("""
                        SELECT * FROM public.company WHERE company_name = :company_name LIMIT 1
                    """),
                    {'company_name': company_name}
                ).fetchone()

            # Insert new profile in Supabase
            db.session.execute(
                db.text("""
                    INSERT INTO public.profile (name, email, role, id_company)
                    VALUES (:name, :email, :role, :id_company)
                """),
                {
                    'name': name,
                    'email': email,
                    'role': role,
                    'id_company': company.id_company
                }
            )
            db.session.commit()

            flash("Registration successful! You can now log in.", "success")
            print("Registration successful")
            return redirect(url_for('main.login'))

        except Exception as e:
            db.session.rollback()
            print(f"ERROR during registration: {e}")
            flash("An error occurred during registration.", "danger")

    return render_template('register.html')


# ==============================
# DASHBOARD ROUTE
# ==============================
@main.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        flash("You must log in first.", "error")
        return redirect(url_for('main.login'))

    name = session.get('name')
    role = session.get('role')
    return render_template('dashboard.html', name=name, role=role)

# ==============================
# LOGOUT ROUTE
# ==============================
@main.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.index'))


# ==============================
# PROFILE PAGE ROUTE
# ==============================
@main.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("You must log in first.", "error")
        return redirect(url_for('main.login'))

    # Get current user
    user = Profile.query.get(session['user_id'])
    company = Company.query.get(user.id_company)

    return render_template(
        'profile.html',
        name=user.name,
        email=user.email,
        company=company.company_name,
        role=user.role
    )


# New route add_feature
@main.route('/projects/<int:project_id>/add-feature', methods=['GET', 'POST'])
def add_feature(project_id):
    # Require login
    if 'user_id' not in session:
        flash("You must log in first.", "error")
        return redirect(url_for('main.login'))
    
    # Role control: Founder OR PM
    if session.get('role') not in ['founder', 'PM']:
        flash("Only Founders or PMs can add new features.", "danger")
        return redirect(url_for('main.projects'))

    # Haal project en company op
    project = Project.query.get_or_404(project_id)
    company = project.company

    if request.method == 'POST':
        # Helper to convert safely to int
        # routes.py (Gecorrigeerde helperfunctie, noem hem to_numeric of to_int)

        def to_numeric(field_name, is_float=False): # <-- Zorg dat dit argument aanwezig is!
            raw = request.form.get(field_name, '').strip()
            if not raw:
                return None
            try:
                return float(raw) if is_float else int(raw)
            except ValueError:
                return None # Zorgt ervoor dat ongeldige input None (NULL) wordt

        # Basic info
        name_feature = request.form.get('name_feature', '').strip()
        description = request.form.get('description', '').strip()

        # ROI fields
        extra_revenue = to_numeric('extra_revenue') # Was 'revenue', nu 'extra_revenue'
        churn_reduction = to_numeric('churn_reduction') # Veld toevoegen voor Churn
        cost_savings = to_numeric('cost_savings')
        investment_hours = to_numeric('investment_hours')
        opex_hours = to_numeric('opex_hours')
        other_costs = to_numeric('other_costs')
        horizon = to_numeric('horizon')
        #roi_percent = request.form.get('roi_percent')  # readonly, string/float

        # TTV fields
        ttm_weeks = to_numeric('ttm_weeks')
        ttbv_weeks = to_numeric('ttbv_weeks')
        ttv_weeks_raw = request.form.get('ttv_weeks', '').strip()
        try:
            ttv_weeks = float(ttv_weeks_raw) if ttv_weeks_raw else None
        except ValueError:
            # Als het een lege string is, zal het al None zijn. Als het een ongeldige string is, 
            # moet je misschien valideren of None retourneren.
            ttv_weeks = None

        # Confidence
        quality_score = request.form.get('quality_score')

        # Validations
        errors = []
        if not name_feature:
            errors.append("Title is required.")

        numeric_fields = {
            'Title': name_feature, # De title check blijft
            'Extra Revenue': extra_revenue, 
            'Churn Reduction': churn_reduction, 
            'Cost savings': cost_savings,
            'Investment hours': investment_hours,
            'OPEX hours': opex_hours,
            'Other costs': other_costs,
            'Horizon': horizon,
            'TTM weeks': ttm_weeks,
            'TTBV weeks': ttbv_weeks
        }
        for label, value in numeric_fields.items():
            if value is None:
                errors.append(f"{label} must be an integer.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template('add_feature.html', project=project, company=company)

        # Create a unique ID for the feature
        new_id = str(uuid.uuid4())

        # BEREKEN ROI WAARDEN
        total_gains = (extra_revenue or 0) + (churn_reduction or 0) + (cost_savings or 0)
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
        ttv_weeks = float(ttv_weeks) # Zet om naar float voor de database

        try:
            feature = Features_ideas(
                id_feature=new_id,              # primary key
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
                expected_profit=expected_profit, # Berekende waarde opslaan
                roi_percent=roi_percent,         # Berekende waarde opslaan
                ttm_weeks=ttm_weeks,
                ttbv_weeks=ttbv_weeks,
                ttv_weeks=ttv_weeks,             # Berekende waarde opslaan
                quality_score=quality_score
            )
            db.session.add(feature)
            db.session.commit()

            flash("Feature saved successfully.", "success")
            return redirect(url_for('main.projects'))

        except Exception as e:
            db.session.rollback()
            print(f"Error while saving feature: {e}")
            flash("An error occurred while saving.", "danger")
            return render_template('add_feature.html', project=project, company=company)

    # GET
    return render_template('add_feature.html', project=project, company=company)


# ==============================
# VECTR CHART OVERZICHT ROUTE
# ==============================
@main.route('/projects/<int:project_id>/vectr-chart', methods=['GET'])
def vectr_chart(project_id):
    if 'user_id' not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for('main.login'))

    user = Profile.query.get(session['user_id'])
    project = Project.query.get_or_404(project_id)

    # Beveiliging: controleer of het project van het bedrijf van de gebruiker is
    if project.id_company != user.id_company:
        flash("You are not allowed to view this chart.", "danger")
        return redirect(url_for('main.projects'))

    # Alle features ophalen die de benodigde data hebben
    features = Features_ideas.query.filter_by(
        id_project=project_id
    ).all()

    # Data transformeren naar een formaat dat geschikt is voor de grafiek (JSON)
    chart_data = []
    for f in features:
        # TtV (weeks) is de X-as (Laag TtV is goed, dus lagere X)
        # ROI (%) is de Y-as (Hoge ROI is goed, dus hogere Y)
        # Confidence (quality_score) bepaalt de grootte/kleur van de bubble
        
        # Zorg ervoor dat we alleen features met geldige data plotten
        if f.roi_percent is not None and f.quality_score is not None and f.ttv_weeks is not None:
            chart_data.append({
                'name': f.name_feature,
                # X-as: Confidence
                'confidence': float(f.quality_score), 
                # Y-as: ROI (%)
                'roi': float(f.roi_percent),
                # Grootte (Bubble Size): TtV (weeks)
                'ttv': float(f.ttv_weeks),
                'id': f.id_feature
            })

    # Geef de data door aan de template
    return render_template('vectr_chart.html', project=project, chart_data=chart_data)



# ==============================
# VIEW FEATURES ROUTE
# ==============================
@main.route('/projects/<int:project_id>/features', methods=['GET'])
def view_features(project_id):
    if 'user_id' not in session:
        flash("U moet eerst inloggen.", "danger")
        return redirect(url_for('main.login'))

    user = Profile.query.get(session['user_id'])
    project = Project.query.get_or_404(project_id)
    company = Company.query.get_or_404(user.id_company)

    # Beveiliging: controleer of het project van het bedrijf van de gebruiker is
    if project.id_company != user.id_company:
        flash("U mag dit project niet bekijken.", "danger")
        return redirect(url_for('main.projects'))

    # Haal alle features op voor dit project
    # Sorteer op de berekende ROI (hoogste eerst)
    features = Features_ideas.query.filter_by(
        id_project=project_id
    ).order_by(Features_ideas.roi_percent.desc()).all()

    return render_template(
        'view_features.html',
        project=project,
        features=features,
        company=company
    )



# ==============================
# PROJECTS OVERVIEW ROUTE
# ==============================
@main.route('/projects')
def projects():
    if 'user_id' not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for('main.login'))

    user = Profile.query.get(session['user_id'])

    # Project + Company name via join
    projects = (
        db.session.query(Project, Company.company_name)
        .join(Company, Project.id_company == Company.id_company)
        .filter(Project.id_company == user.id_company)
        .order_by(Project.id_project.desc())
        .all()
    )

    return render_template('projects.html', projects=projects)


@main.route('/add_project', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for('main.login'))
    
    # Role control: Founder OR PM
    if session.get('role') not in ['founder', 'PM']:
        flash("Only Founders and Project Managers are allowed to add new projects.", "danger")
        return redirect(url_for('main.projects'))

    # Get logged in user
    user = Profile.query.get(session['user_id'])
    user_company = Company.query.filter_by(id_company=user.id_company).first()

    if request.method == 'POST':
        project_name = request.form.get("project_name")
        company_id = user_company.id_company  # auto fill

        new_project = Project(
            project_name=project_name,
            id_company=company_id
        )

        db.session.add(new_project)
        db.session.commit()

        flash("Project added successfully.", "success")
        return redirect(url_for('main.projects'))

    # ⬇️ Only pass 1 company (from user)
    return render_template(
        "add_project.html",
        company=user_company
    )

# ==============================
# EDIT PROJECT
# ==============================
@main.route('/projects/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for('main.login'))

    user = Profile.query.get(session['user_id'])
    project = Project.query.get_or_404(project_id)

    # Security: only projects from own company
    if project.id_company != user.id_company:
        flash("You are not allowed to edit this project.", "danger")
        return redirect(url_for('main.projects'))

    if request.method == 'POST':
        new_name = request.form.get("project_name", "").strip()

        if not new_name:
            flash("Project name is required.", "danger")
            return render_template("edit_project.html", project=project)

        project.project_name = new_name
        db.session.commit()

        flash("Project updated successfully.", "success")
        return redirect(url_for('main.projects'))

    # GET
    return render_template("edit_project.html", project=project)


# ==============================
# DELETE PROJECT
# ==============================
@main.route('/projects/delete/<int:project_id>')
def delete_project(project_id):
    if 'user_id' not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for('main.login'))

    user = Profile.query.get(session['user_id'])
    project = Project.query.get_or_404(project_id)

    # Security: only own company
    if project.id_company != user.id_company:
        flash("You are not allowed to delete this project.", "danger")
        return redirect(url_for('main.projects'))

    try:
        db.session.delete(project)   # cascade deletes features_ideas too
        db.session.commit()
        flash("Project deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        print(f"Error while deleting project: {e}")
        flash("An error occurred while deleting the project.", "danger")

    return redirect(url_for('main.projects'))

# ==============================
# ROADMAP ROUTES 
# ==============================


@main.route('/roadmap/add/<int:project_id>', methods=['GET', 'POST'])
def add_roadmap(project_id):
    if 'user_id' not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for('main.login'))

    # Only founders can create roadmaps
    if session.get('role') != 'founder':
        flash("Only Founders can create roadmaps.", "danger")
        return redirect(url_for('main.projects'))

    user = Profile.query.get(session['user_id'])
    project = Project.query.get_or_404(project_id)

    # Must belong to same company
    if project.id_company != user.id_company:
        flash("You are not allowed to add a roadmap to this project.", "danger")
        return redirect(url_for('main.projects'))

    if request.method == 'POST':
        quarter = request.form.get("quarter")
        team_size = request.form.get("team_size")
        sprint_capacity = request.form.get("sprint_capacity")
        budget_allocation = request.form.get("budget_allocation")

        # Check if this quarter already has a roadmap
        existing = Roadmap.query.filter_by(
            id_project=project_id,
            quarter=quarter
        ).first()

        if existing:
            flash("This project already has a roadmap for that quarter.", "danger")
            return render_template('add_roadmap.html', project=project)


        # Create roadmap
        roadmap = Roadmap(
            id_project=project_id,
            quarter=quarter,
            team_size=int(team_size),
            sprint_capacity=int(sprint_capacity),
            budget_allocation=int(budget_allocation)
        )

        db.session.add(roadmap)
        db.session.commit()

        flash("Roadmap created successfully!", "success")
        return redirect(url_for('main.roadmap_overview', project_id=project_id))

    return render_template('add_roadmap.html', project=project)


@main.route('/roadmap/<int:project_id>')
def roadmap_overview(project_id):
    if 'user_id' not in session:
        flash("You must log in first.", "danger")
        return redirect(url_for('main.login'))

    user = Profile.query.get(session['user_id'])
    project = Project.query.get_or_404(project_id)

    # Check company ownership
    if project.id_company != user.id_company:
        flash("You are not allowed to view this roadmap.", "danger")
        return redirect(url_for('main.projects'))

    # Alle roadmaps van dit project ophalen
    roadmaps = project.roadmaps

    return render_template(
        "roadmap_overview.html",
        project=project,
        roadmaps=roadmaps
    )

