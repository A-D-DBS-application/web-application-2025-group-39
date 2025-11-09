from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from app import db
from app.models import Profile, Company

# Blueprint aanmaken
main = Blueprint('main', __name__)

# ==============================
# 🏠 INDEX ROUTE
# ==============================
@main.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        flash("Deze actie is niet toegestaan.", "error")
        return redirect(url_for('main.login'))

    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))

    return render_template('index.html')


# ==============================
# 🔐 LOGIN ROUTE
# ==============================
@main.route('/login', methods=['GET', 'POST'])
def login():
    print("🟢 Login route gestart")
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')

        print(f"📨 Login poging ontvangen: username={username}, email={email}")

        # ✅ Zoeken naar gebruiker in profiel met ORM
        user = Profile.query.filter_by(name=username, email=email).first()

        if user:
            session['user_id'] = user.id_profile
            session['username'] = user.name
            session['role'] = user.role

            flash("Succesvol ingelogd!", "success")
            print("✅ Login succesvol")
            return redirect(url_for('main.dashboard'))
        else:
            flash("Ongeldige gebruikersnaam of e-mail.", "error")
            print("❌ Onjuiste gegevens")

    return render_template('login.html')


# ==============================
# 👤 REGISTER ROUTE (WERKT MET SUPABASE STRUCTUUR)
# ==============================
@main.route('/register', methods=['GET', 'POST'])
def register():
    print("🟢 Register route gestart")

    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        company_name = request.form.get('company_name')

        print(f"📨 Gehele request.form inhoud: {request.form}")
        print(f"📨 Gegevens ontvangen: {username} {email} {role} {company_name}")

        try:
            # ✅ Bedrijf zoeken (of aanmaken) met ruwe SQL
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
                    'name': username,
                    'email': email,
                    'role': role,
                    'id_company': company.id_company
                }
            )
            db.session.commit()

            flash("✅ Registratie succesvol! Je kunt nu inloggen.", "success")
            print("✅ Registratie succesvol")
            return redirect(url_for('main.login'))

        except Exception as e:
            db.session.rollback()
            print(f"❌ FOUT tijdens registratie: {e}")
            flash("Er is een fout opgetreden tijdens registratie.", "danger")

    return render_template('register.html')


# ==============================
# 🧭 DASHBOARD ROUTE
# ==============================
@main.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:
        flash("Je moet eerst inloggen.", "error")
        return redirect(url_for('main.login'))

    username = session.get('username')
    role = session.get('role')
    return render_template('dashboard.html', username=username, role=role)


# ==============================
# 🚪 LOGOUT ROUTE
# ==============================
@main.route('/logout')
def logout():
    session.clear()
    flash("Je bent uitgelogd.", "info")
    return redirect(url_for('main.login'))
