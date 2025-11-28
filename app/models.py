from . import db  # haal db uit __init__.py
import datetime  # datetime importeren
from .security import hash_password, verify_password, needs_rehash

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
    password_hash = db.Column(db.String, nullable=False)

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

   # Helpers voor wachtwoordbeheer
    def set_password(self, plain_password: str):
        self.password_hash = hash_password(plain_password)

    def check_password(self, plain_password: str) -> bool:
        return verify_password(self.password_hash, plain_password)

    def maybe_upgrade_hash(self, plain_password: str) -> bool:
        if needs_rehash(self.password_hash):
            self.set_password(plain_password)
            return True
        return False

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

    roadmaps = db.relationship(
    "Roadmap",
    back_populates="project",
    cascade="all, delete",
    passive_deletes=True
    )


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

    # Primary key (UUID string)
    id_feature = db.Column(db.String, primary_key=True)

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

    # Basic info
    name_feature = db.Column(db.String, nullable=False)
    description = db.Column(db.Text)

    # ROI fields
    horizon = db.Column(db.Integer)
    extra_revenue = db.Column(db.Integer)
    churn_reduction = db.Column(db.Integer)
    cost_savings = db.Column(db.Integer)
    investment_hours = db.Column(db.Integer)
    opex_hours = db.Column(db.Integer)
    other_costs = db.Column(db.Integer)
    

    # TTV fields
    ttm_weeks = db.Column(db.Integer)
    ttbv_weeks = db.Column(db.Integer)

    # Confidence
    quality_score = db.Column(db.Float)

    #berekende values:
    expected_profit = db.Column(db.Integer)
    roi_percent = db.Column(db.Float)
    ttv_weeks = db.Column(db.Float)

    # Metadata
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relatie terug naar project
    project = db.relationship("Project", back_populates="features_ideas")


class Roadmap(db.Model):
    __tablename__ = 'roadmap'
    __table_args__ = {'schema': 'public'}

    id_roadmap = db.Column(db.Integer, primary_key=True)

    # Foreign key naar project
    id_project = db.Column(
        db.Integer,
        db.ForeignKey('public.project.id_project', ondelete="CASCADE"),
        nullable=False
    )

    # Roadmap velden
    quarter = db.Column(db.String, nullable=False)  # bijv. "Q1 2025"
    team_size = db.Column(db.Integer, nullable=False)
    sprint_capacity = db.Column(db.Integer, nullable=False)
    budget_allocation = db.Column(db.Integer, nullable=False)
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)


    # Relatie terug naar Project
    project = db.relationship("Project", back_populates="roadmaps")

    # Roadmap → Milestones
    milestones = db.relationship(
        "Milestone",
        back_populates="roadmap",
        cascade="all, delete",
        passive_deletes=True
    )



class Milestone(db.Model):
    __tablename__ = 'milestone'
    __table_args__ = {'schema': 'public'}

    id_milestone = db.Column(db.Integer, primary_key=True)

    # Foreign key naar roadmap
    id_roadmap = db.Column(
        db.Integer,
        db.ForeignKey('public.roadmap.id_roadmap', ondelete="CASCADE"),
        nullable=False
    )

    # Milestone velden
    name = db.Column(db.String, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    goal = db.Column(db.String)
    status = db.Column(db.String)  # Planned / In Progress / Done

    roadmap = db.relationship("Roadmap", back_populates="milestones")

