# app/routes.py

from flask import Blueprint, request, redirect, url_for, render_template, session
from .models import db, User, Listing

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        listings = Listing.query.filter_by(user_id=user.id).all()  # Fetch listings for logged-in user
        return render_template('index.html', username=user.username, listings=listings)
    return render_template('index.html', username=None)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        role = request.form['role']
        company_name = request.form['company_name']
        
        print(f"📝 Registratie poging: {username}, {name}, {role}, {company_name}")  # ✅ Debug print
        
        try:
            # Controleer of gebruiker al bestaat in Supabase
            print("🔍 Controleren of gebruiker bestaat...")
            existing_user = supabase.table('users').select('*').eq('username', username).execute()
            
            print(f"📊 Bestaande gebruiker response: {existing_user}")
            
            if existing_user.data:
                flash('Gebruikersnaam bestaat al', 'error')
                return render_template('register.html')
            
            # Nieuwe gebruiker toevoegen aan Supabase
            new_user = {
                'username': username,
                'name': name,
                'role': role,
                'company_name': company_name
            }
            
            print(f"💾 Nieuwe gebruiker opslaan: {new_user}")  # ✅ Debug print
            
            response = supabase.table('users').insert(new_user).execute()
            
            print(f"📨 Supabase response: {response}")  # ✅ Debug print
            
            if response.data:
                flash('Registratie succesvol! Je kunt nu inloggen.', 'success')
                return redirect(url_for('main.login'))
            else:
                flash('Registratie mislukt', 'error')
                
        except Exception as e:
            print(f"❌ FOUT in registratie: {str(e)}")  # ✅ Debug print
            flash(f'Registratie error: {str(e)}', 'error')
    
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        user = User.query.filter_by(username=username).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('main.index'))
        return 'User not found'
    return render_template('login.html')

@main.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('main.index'))

@main.route('/add-listing', methods=['GET', 'POST'])
def add_listing():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        listing_name = request.form['listing_name']
        price = float(request.form['price'])
        new_listing = Listing(listing_name=listing_name, price=price, user_id=session['user_id'])
        db.session.add(new_listing)
        db.session.commit()
        return redirect(url_for('main.listings'))

    return render_template('add_listing.html')

@main.route('/listings')
def listings():
    all_listings = Listing.query.all()
    return render_template('listings.html', listings=all_listings)