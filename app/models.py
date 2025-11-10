from . import db  # haal db uit __init__.py
import datetime #datetime importeren 

class Company(db.Model):
    __tablename__ = 'company'
    __table_args__ = {'schema': 'public'} #tabel aanmaken in database
    # Primary key
    companyid = db.Column(db.String, primary_key=True)  

    # company information
    company_name = db.Column(db.String, nullable=False)
    #relaties:
    users = db.relationship('User', backref='company', lazy=True)
    projects = db.relationship('Project', backref='company', lazy=True)



class Profile(db.Model):
    __tablename__ = 'profile'
    __table_args__ = {'schema': 'public'}
    # Primary key
    id_profile = db.Column(db.Integer, primary_key=True) # Using id_profile as primary key for consistency with your table
    #user information
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    role = db.Column(db.String, nullable=True)
    # Foreign keys
    id_company = db.Column(db.Integer, db.ForeignKey('public.company.id_company'))

    company = db.relationship('Company', back_populates='profiles')
    #tijd van aanmaak Profile
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Profile {self.name}>"

class Project(db.Model):
    __tablename__ = 'project'
    __table_args__ = {'schema': 'public'}

    # Primaire sleutel
    id_project= db.Column(db.String, primary_key=True)

    # Foreign keys
    companyid = db.Column(db.String, db.ForeignKey('company.companyid'), nullable=False)  # Verwijst naar company.companyid
    #eigenschappen project
    project_name = db.Column(db.String, nullable=False)
    # Metadata
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)  # Datum van project maken
    #relaties
    features_ideas = db.relationship('Features_ideas', backref='project', lazy=True)
    #tijd van aanmaak Project
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Features_ideas(db.Model):
    __tablename__ = 'features'
    __table_args__ = {'schema': 'public'}
    # Primary key
    id_feature = db.Column(db.String, primary_key=True)  # Using featureid as primary key for consistency with your table

    # Foreign keys
    companyid = db.Column(db.String, db.ForeignKey('company.companyid'), nullable=False)  # Verwijst naar company.companyid
    id_project = db.Column(db.String, db.ForeignKey('project.id_project'), nullable=False)
    # feature information
    name_feature = db.Column(db.String, nullable=False)
    gains = db.Column(db.Integer, nullable=False)
    costs = db.Column(db.Integer, nullable=False)
    churn_OPEX = db.Column(db.Integer, nullable=False)
    opp_cost = db.Column(db.Integer, nullable=False)
    market_value = db.Column(db.Integer, nullable=False)
    business_value = db.Column(db.Integer, nullable=False)
    validation_stage = db.Column(db.Integer, nullable=False)
    quality_score = db.Column(db.Integer, nullable=False)

    # Metadata
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)
