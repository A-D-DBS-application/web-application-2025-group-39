from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import db
from app.models import Profile, Company, Project, Features_ideas

# Blueprint aanmaken
main = Blueprint('main', __name__)

# ==============================
# INDEX ROUTE
# ==============================
@main.route('/', methods=['GET'])
def index():
    # Als ingelogd → ga naar dashboard
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    # Anders → startpagina tonen
    return render_template('index.html')

# ==============================
# LOGIN ROUTE
# ==============================
@main.route('/login', methods=['GET', 'POST'])
def login():
    print("🟢 Login route gestart")
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')

        print(f"📨 Login poging ontvangen: name={name}, email={email}")

        # Zoeken naar gebruiker in profiel met ORM
        user = Profile.query.filter_by(name=name, email=email).first()

        if user:
            session['user_id'] = user.id_profile
            session['name'] = user.name
            session['role'] = user.role

            flash("Successfully logged in!", "success")
            print("Login succesvol")
            return redirect(url_for('main.dashboard'))
        else:
            flash("Invalid name or email.", "error")
            print("Onjuiste gegevens")

    return render_template('login.html')


# ==============================
# REGISTER ROUTE (WERKT MET SUPABASE STRUCTUUR)
# ==============================
@main.route('/register', methods=['GET', 'POST'])
def register():
    print("Register route gestart")

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        company_name = request.form.get('company_name')

        print(f"Gehele request.form inhoud: {request.form}")
        print(f"Gegevens ontvangen: {name} {email} {role} {company_name}")

        try:
            # Bedrijf zoeken (of aanmaken) met ruwe SQL
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

            # ✅ Nieuw profiel invoegen in Supabase
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
            print("Registratie succesvol")
            return redirect(url_for('main.login'))

        except Exception as e:
            db.session.rollback()
            print(f"FOUT tijdens registratie: {e}")
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

    # Haal huidige gebruiker op
    user = Profile.query.get(session['user_id'])
    company = Company.query.get(user.id_company)

    return render_template(
        'profile.html',
        name=user.name,
        email=user.email,
        company=company.company_name,
        role=user.role
    )


#new route add_feature
@main.route('/add-feature', methods=['GET', 'POST'])
def add_feature():
    # Require login
    if 'user_id' not in session:
        flash("You must log in first.", "error")
        return redirect(url_for('main.login'))

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
                id_feature=new_id,
                id_company=id_company,
                id_project=id_project,
                name_feature=name_feature,
                gains=gains,
                costs=costs,
                churn_OPEX=churn_OPEX,
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
            print(f"Fout bij opslaan feature: {e}")
            flash("An error occurred while saving.", "danger")
            return render_template('add_feature.html', companies=companies)

    # GET: render page
    return render_template('add_feature.html', companies=companies)

