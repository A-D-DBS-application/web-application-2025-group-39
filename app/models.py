from . import db  # haal db uit __init__.py
import datetime  # datetime importeren


class Company(db.Model):
    __tablename__ = 'company'
    __table_args__ = {'schema': 'public'}  # tabel aanmaken in database

    # Primary key
    id_company = db.Column(db.Integer, primary_key=True)

    # company information
    company_name = db.Column(db.String, nullable=False)

    # relaties:
    profiles = db.relationship('Profile', back_populates='company', lazy=True)
    projects = db.relationship('Project', back_populates='company', lazy=True)


class Profile(db.Model):
    __tablename__ = 'profile'
    __table_args__ = {'schema': 'public'}

    # Primary key
    id_profile = db.Column(db.Integer, primary_key=True)

    # user information
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    role = db.Column(db.String, nullable=True)

    # Foreign keys
    id_company = db.Column(
        db.Integer,
        db.ForeignKey('public.company.id_company'),
        nullable=False
    )

    # relationship
    company = db.relationship('Company', back_populates='profiles')

    # tijd van aanmaak Profile
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<Profile {self.name}>"


class Project(db.Model):
    __tablename__ = 'project'
    __table_args__ = {'schema': 'public'}

    # Primaire sleutel
    id_project = db.Column(db.Integer, primary_key=True)

    # Foreign key → company
    id_company = db.Column(
        db.Integer,
        db.ForeignKey('public.company.id_company'),
        nullable=False
    )

    # project info
    project_name = db.Column(db.String, nullable=False)

    # metadata
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # relaties
    company = db.relationship("Company", back_populates="projects")

    # alle features_ideas die aan dit project hangen
    features_ideas = db.relationship(
        "Features_ideas",
        back_populates="project",
        cascade="all, delete",   # bij delete project → bijhorende features_ideas ook weg
        passive_deletes=True
    )


class Features_ideas(db.Model):
    __tablename__ = 'features_ideas'
    __table_args__ = {'schema': 'public'}

    # Primary key
    id_feature = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    id_company = db.Column(
        db.Integer,
        db.ForeignKey('public.company.id_company'),
        nullable=False
    )
    id_project = db.Column(
        db.Integer,
        db.ForeignKey('public.project.id_project'),
        nullable=False
    )

    # feature informatie
    name_feature = db.Column(db.String, nullable=False)
    gains = db.Column(db.Integer, nullable=False)
    costs = db.Column(db.Integer, nullable=False)

    # ⚠️ kolomnamen exact zoals in Supabase (kleine letters)
    churn_opex = db.Column(db.Integer, nullable=False)
    opp_cost = db.Column(db.Integer, nullable=False)

    market_value = db.Column(db.Integer, nullable=False)
    business_value = db.Column(db.Integer, nullable=False)
    validation_stage = db.Column(db.Integer, nullable=False)
    quality_score = db.Column(db.Integer, nullable=False)

    # metadata
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # relatie terug naar project
    project = db.relationship("Project", back_populates="features_ideas")
