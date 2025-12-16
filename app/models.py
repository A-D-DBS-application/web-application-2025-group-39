from . import db  # haal db uit __init__.py
import datetime  # datetime importeren
from .security import hash_password, verify_password, needs_rehash
from sqlalchemy import desc

# ------------------------------------
# Confidence Levels
# ------------------------------------
CONFIDENCE_LEVELS = [
    (0.0,  "No Longer Relevant"),
    (0.01, "Self Conviction"),
    (0.03, "Pitch Deck"),
    (0.1,  "Thematic Support"),
    (0.2,  "Other’s Opinion"),
    (0.5,  "Estimates & Plans"),
    (1.0,  "Anecdotal Evidence"),
    (2.0,  "Market Data"),
    (3.0,  "User/Customer Evidence"),
    (7.0,  "Test Results"),
    (10.0, "Launch Data"),
]


# =====================================================
# COMPANY
# =====================================================
class Company(db.Model):
    __tablename__ = "company"
    __table_args__ = {"schema": "public"}                                           # Gebruik het 'public' schema 
    
    # Primary key
    id_company = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String, nullable=False)

    # Relaties:
    profiles = db.relationship("Profile", back_populates="company", lazy=True)      # Company (1) <---> (Many) Profile
    projects = db.relationship("Project", back_populates="company", lazy=True)      # Company (1) <---> (Many) Project



# =====================================================
# PROFILE
# =====================================================
class Profile(db.Model):
    __tablename__ = "profile"
    __table_args__ = {"schema": "public"}

    # primary key
    id_profile = db.Column(db.Integer, primary_key=True)  

    # foreign key
    id_company = db.Column(                                                         
        db.Integer, db.ForeignKey("public.company.id_company"), nullable=False
    )                           
    
    # basis info 
    name = db.Column(db.String, nullable=False)                                     # naam, moet ingevuld worden, (nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)                  # email met max 120 tekens en is unique
    role = db.Column(db.String, nullable=True)
    password_hash = db.Column(db.String, nullable=False)                            # gehashte wachtwoord
    
    #relaties:
    company = db.relationship("Company", back_populates="profiles")                 # relatie: Profile (Many) <---> (1) Company
    
    #metadata
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)            # Tijdstip van creatie (standaard UTC)

    def __repr__(self):
        return f"<Profile {self.name}>"

    # Helpers voor wachtwoordbeheer
    def set_password(self, plain_password: str):                                    # hasht en stelt het wachtwoord in.
        self.password_hash = hash_password(plain_password)

    def check_password(self, plain_password: str) -> bool:                          # controleert het tekstwachtwoord tegen de hash.
        return verify_password(self.password_hash, plain_password)

    def maybe_upgrade_hash(self, plain_password: str) -> bool:                      # controleert of de hash een upgrade nodig heeft en voert deze uit indien nodig.
        if needs_rehash(self.password_hash):
            self.set_password(plain_password)
            return True
        return False

# =====================================================
# PROJECT
# =====================================================
class Project(db.Model):
    __tablename__ = "project"
    __table_args__ = {"schema": "public"}

    # Primary key
    id_project = db.Column(db.Integer, primary_key=True)
    # foreign key (relatie met company)
    id_company = db.Column(
        db.Integer, db.ForeignKey("public.company.id_company"), nullable=False
    )

    project_name = db.Column(db.String, nullable=False)
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # TtV Schalings limiet
    ttm_low_limit = db.Column(db.Float)
    ttm_high_limit = db.Column(db.Float)
    ttbv_low_limit = db.Column(db.Float)
    ttbv_high_limit = db.Column(db.Float)

    # relaties 
    company = db.relationship("Company", back_populates="projects")                 # relatie: Project (Many) <---> (1) Company
    roadmaps = db.relationship(                                                     # relatie: Project (1) <---> (Many) Roadmap
        "Roadmap", back_populates="project", cascade="all, delete", passive_deletes=True
    )                                                                               # cascade="all, delete" zorgt ervoor dat Roadmaps worden verwijderd als het Project wordt verwijderd

    features_ideas = db.relationship(                                               # relatie: Project (1) <---> (Many) Features_ideas  
        "Features_ideas",
        back_populates="project",
        cascade="all, delete",
        passive_deletes=True,
    )


# =====================================================
# FEATURES / IDEAS
# =====================================================
class Features_ideas(db.Model):
    __tablename__ = "features_ideas"
    __table_args__ = {"schema": "public"}

    # Primary key (UUID string)
    id_feature = db.Column(db.String, primary_key=True)

    # Foreign keys
    id_company = db.Column(
        db.Integer, db.ForeignKey("public.company.id_company"), nullable=False
    )
    id_project = db.Column(
        db.Integer, db.ForeignKey("public.project.id_project"), nullable=False
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
    hourly_rate = db.Column(db.Integer)
    opex = db.Column(db.Integer)
    other_costs = db.Column(db.Integer)

    # TTV fields
    ttm_weeks = db.Column(db.Integer)
    ttbv_weeks = db.Column(db.Integer)

    # Confidence
    quality_score = db.Column(db.Float)

    # calculated values
    expected_profit = db.Column(db.Integer)
    roi_percent = db.Column(db.Float)
    ttv_weeks = db.Column(db.Float)

    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    project = db.relationship("Project", back_populates="features_ideas")
    
    # Outlier warning status
    warning_dismissed = db.Column(db.Boolean, default=False, nullable=False)

    decisions = db.relationship(
        "Decision",
        back_populates="feature",
        cascade="all, delete",
        passive_deletes=True,
    )

    @property                                                                       # berekeningen of database-queries uit te voeren wanneer een attribuut wordt opgevraagd
    def latest_decision(self):                                                      # haalt de meest recente Decision op basis van createdat
        return (
            Decision.query.filter_by(id_feature=self.id_feature)
            .order_by(desc(Decision.createdat))
            .first()
        )



# =====================================================
# ROADMAP
# =====================================================
class Roadmap(db.Model):
    __tablename__ = "roadmap"
    __table_args__ = {"schema": "public"}

    id_roadmap = db.Column(db.Integer, primary_key=True)

    id_project = db.Column(
        db.Integer,
        db.ForeignKey("public.project.id_project", ondelete="CASCADE"),
        nullable=False,
    )

    # Roadmap periodes blijven strings zodat de originele invoer bewaard blijft, zijn dates
    start_roadmap = db.Column(db.Date, nullable=False)  
    end_roadmap = db.Column(db.Date, nullable=False)
    # Capaciteit en budget mogen nu decimalen bevatten (bijv. 2.5 FTE)
    # Float i.p.v. Integer voorkomt dat valid decimals worden afgerond of geweigerd
    time_capacity = db.Column(db.Float, nullable=False)
    budget_allocation = db.Column(db.Float, nullable=False)
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    project = db.relationship("Project", back_populates="roadmaps")

    milestones = db.relationship(
        "Milestone",
        back_populates="roadmap",
        cascade="all, delete",
        passive_deletes=True,
    )


# =====================================================
# Many-to-Many relatie tussen Milestone en Features_ideas beheert
# =====================================================
class MilestoneFeature(db.Model):
    __tablename__ = "milestone_features"
    __table_args__ = {"schema": "public"}
    
    milestone_id = db.Column(
        db.Integer,
        db.ForeignKey("public.milestone.id_milestone", ondelete="CASCADE"),
        primary_key=True,
    )
    
    id_feature = db.Column(
        db.String,
        db.ForeignKey("public.features_ideas.id_feature", ondelete="CASCADE"),
        primary_key=True,
    )

    # RELATIES NAAR DE HOOFDMODELLEN (gebruikt in de joins)
    milestone = db.relationship("Milestone", backref="features_links")
    feature = db.relationship("Features_ideas", backref="milestones_links")

# =====================================================
# MILESTONE
# =====================================================
class Milestone(db.Model):
    __tablename__ = "milestone"
    __table_args__ = {"schema": "public"}

    id_milestone = db.Column(db.Integer, primary_key=True)

    # Many-to-many: milestone ↔ features
    features = db.relationship(
        "Features_ideas",
        secondary="public.milestone_features", # GEBRUIK DE TABELNAAM ALS STRING
        
        # Specificeer de joins (deze zijn essentieel)
        primaryjoin="Milestone.id_milestone == MilestoneFeature.milestone_id",
        secondaryjoin="Features_ideas.id_feature == MilestoneFeature.id_feature",

        backref="milestones",
        lazy="select",
    )

    id_roadmap = db.Column(
        db.Integer,
        db.ForeignKey("public.roadmap.id_roadmap", ondelete="CASCADE"),
        nullable=False,
    )

    name = db.Column(db.String, nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    goal = db.Column(db.String)
    status = db.Column(db.String)  # Planned / In Progress / Done

    roadmap = db.relationship("Roadmap", back_populates="milestones")


# =====================================================
# EVIDENCE
# =====================================================
class Evidence(db.Model):
    __tablename__ = "evidence"
    __table_args__ = {"schema": "public"}

    id_evidence = db.Column(db.Integer, primary_key=True)

    id_feature = db.Column(
        db.String, db.ForeignKey("public.features_ideas.id_feature"), nullable=False
    )

    id_company = db.Column(
        db.Integer, db.ForeignKey("public.company.id_company"), nullable=False
    )


    title = db.Column(db.String)
    type = db.Column(db.String)                                                         # Type bewijs (bijv. "Interview", "A/B Test", "Marktanalyse")
    source = db.Column(db.String)                                                       # Bron (bijv. naam van de test, link naar document)
    description = db.Column(db.Text)
    attachment_url = db.Column(db.Text)                                                 # Link naar het bewijs

    # NEW SYSTEM
    old_confidence = db.Column(db.Float)  # feature score BEFORE adding this evidence
    new_confidence = db.Column(db.Float)  # confidence level selected from list

    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    feature = db.relationship("Features_ideas", backref="evidence")


# =====================================================
# DECISION
# =====================================================
class Decision(db.Model):
    __tablename__ = "decision"
    __table_args__ = (
        db.UniqueConstraint(
            "id_feature", "id_profile", name="uq_decision_feature_profile"
        ),
        {"schema": "public"},
    )

    id_decision = db.Column(db.Integer, primary_key=True)

    id_feature = db.Column(
        db.String,
        db.ForeignKey("public.features_ideas.id_feature", ondelete="CASCADE"),
        nullable=False,
    )

    id_profile = db.Column(
        db.Integer,
        db.ForeignKey("public.profile.id_profile", ondelete="CASCADE"),
        nullable=False,
    )

    id_company = db.Column(
        db.Integer, db.ForeignKey("public.company.id_company"), nullable=False
    )

    decision_type = db.Column(db.String(50), nullable=False)

    createdat = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    feature = db.relationship("Features_ideas", back_populates="decisions")
    profile = db.relationship("Profile")

# =====================================================
# PROJECT CHAT MESSAGE
# =====================================================
class ProjectChatMessage(db.Model):
    __tablename__ = "project_chat_message"
    __table_args__ = {"schema": "public"}

    id_message = db.Column(db.Integer, primary_key=True)

    id_project = db.Column(
        db.Integer,
        db.ForeignKey("public.project.id_project", ondelete="CASCADE"),
        nullable=False,
    )

    id_profile = db.Column(
        db.Integer,
        db.ForeignKey("public.profile.id_profile", ondelete="CASCADE"),
        nullable=False,
    )

    content = db.Column(db.Text, nullable=False)
    createdat = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    sender = db.relationship("Profile")
    project = db.relationship("Project")
