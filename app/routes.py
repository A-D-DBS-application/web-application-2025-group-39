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
@main.route('/add-feature', methods=['GET', 'POST'])
def add_feature():
    # Require login
    if 'user_id' not in session:
        flash("You must log in first.", "error")
        return redirect(url_for('main.login'))
    
    # Role control: Founder OR PM
    if session.get('role') not in ['founder', 'PM']:
        flash("Only Founders or PMs can add new features.", "danger")
        return redirect(url_for('main.projects'))

    # Load companies for the dropdown (ORM)
    companies = Company.query.order_by(Company.company_name.asc()).all()

    if request.method == 'POST':
        # Read form fields
        name_feature = request.form.get('name_feature', '').strip()
        id_company = request.form.get('id_company', '').strip()
        id_project = request.form.get('id_project', '').strip()

        # Numeric fields: validate and convert to int
        def to_int(field_name):
            raw = request.form.get(field_name, '').strip()
            try:
                return int(raw)
            except ValueError:
                return None

        gains = to_int('gains')
        costs = to_int('costs')
        churn_OPEX = to_int('churn_OPEX')
        opp_cost = to_int('opp_cost')
        market_value = to_int('market_value')
        business_value = to_int('business_value')
        validation_stage = to_int('validation_stage')
        quality_score = to_int('quality_score')

        # Simple server-side validations
        errors = []
        if not name_feature:
            errors.append("Title is required.")
        if not id_company:
            errors.append("Company is required.")
        if not id_project:
            errors.append("Project is required.")

        numeric_fields = {
            'Gains': gains,
            'Costs': costs,
            'Churn / OPEX': churn_OPEX,
            'Opportunity cost': opp_cost,
            'Market value': market_value,
            'Business value': business_value,
            'Validation stage': validation_stage,
            'Quality score': quality_score
        }
        for label, value in numeric_fields.items():
            if value is None:
                errors.append(f"{label} must be an integer.")

        # Ensure company and project exist in DB
        company_exists = Company.query.filter_by(id_company=id_company).first()
        project_exists = Project.query.filter_by(id_project=id_project, id_company=id_company).first()

        if not company_exists:
            errors.append("Selected company does not exist.")
        if not project_exists:
            errors.append("Selected project does not exist or does not belong to this company.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template('add_feature.html', companies=companies)

        # Create a unique ID for the feature (string PK)
        new_id = str(uuid.uuid4())

        try:
            feature = Features_ideas(
                id_company=int(id_company),
                id_project=int(id_project),
                name_feature=name_feature,
                gains=gains,
                costs=costs,
                churn_opex=churn_OPEX,          # column name in model
                opp_cost=opp_cost,
                market_value=market_value,
                business_value=business_value,
                validation_stage=validation_stage,
                quality_score=quality_score
            )
            db.session.add(feature)
            db.session.commit()

            flash("Feature saved successfully.", "success")
            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"Error while saving feature: {e}")
            flash("An error occurred while saving.", "danger")
            return render_template('add_feature.html', companies=companies)

    # GET: render page
    return render_template('add_feature.html', companies=companies)

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

        flash("Project added successfully!", "success")
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

        flash("Project updated successfully!", "success")
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
        flash("Project deleted successfully!", "success")
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

