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
    __table_args__ = {"schema": "public"}

    id_company = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String, nullable=False)

    profiles = db.relationship("Profile", back_populates="company", lazy=True)
    projects = db.relationship("Project", back_populates="company", lazy=True)


# =====================================================
# PROFILE
# =====================================================
class Profile(db.Model):
    __tablename__ = "profile"
    __table_args__ = {"schema": "public"}

    id_profile = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String, nullable=True)
    password_hash = db.Column(db.String, nullable=False)

    id_company = db.Column(
        db.Integer, db.ForeignKey("public.company.id_company"), nullable=False
    )

    company = db.relationship("Company", back_populates="profiles")

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


# =====================================================
# PROJECT
# =====================================================
class Project(db.Model):
    __tablename__ = "project"
    __table_args__ = {"schema": "public"}

    id_project = db.Column(db.Integer, primary_key=True)

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

    company = db.relationship("Company", back_populates="projects")

    roadmaps = db.relationship(
        "Roadmap", back_populates="project", cascade="all, delete", passive_deletes=True
    )

    features_ideas = db.relationship(
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
    opex_hours = db.Column(db.Integer)
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

    decisions = db.relationship(
        "Decision",
        back_populates="feature",
        cascade="all, delete",
        passive_deletes=True,
    )

    @property
    def latest_decision(self):
        """Haalt de meest recente Decision op basis van created_at."""
        return (
            Decision.query.filter_by(id_feature=self.id_feature)
            .order_by(desc(Decision.created_at))
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

    # Roadmap periodes blijven strings zodat de originele invoer bewaard blijft
    start_roadmap = db.Column(db.String, nullable=False)  
    end_roadmap = db.Column(db.String, nullable=False)
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
# ASSOCIATION TABLE: Many-to-Many relatie tussen Milestone en Features_ideas beheert
# =====================================================
class MilestoneFeature(db.Model):
    __tablename__ = "milestone_features"
    __table_args__ = {"schema": "public"}
    
    milestone_id = db.Column(
        db.Integer,
        db.ForeignKey("public.milestone.id_milestone", ondelete="CASCADE"),
        primary_key=True,
    )
    
    feature_id = db.Column(
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
        secondaryjoin="Features_ideas.id_feature == MilestoneFeature.feature_id",

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
    type = db.Column(db.String)
    source = db.Column(db.String)
    description = db.Column(db.Text)
    attachment_url = db.Column(db.Text)

    # NEW SYSTEM
    old_confidence = db.Column(db.Float)  # feature score BEFORE adding this evidence
    new_confidence = db.Column(db.Float)  # confidence level selected from list

    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    feature = db.relationship("Features_ideas", backref="evidence")


# =====================================================
# DECISION
# =====================================================
class Decision(db.Model):
    __tablename__ = "decision"
    __table_args__ = {"schema": "public"}

    id_decision = db.Column(db.Integer, primary_key=True)

    id_feature = db.Column(
        db.String,
        db.ForeignKey("public.features_ideas.id_feature", ondelete="CASCADE"),
        nullable=False,
    )

    id_company = db.Column(
        db.Integer, db.ForeignKey("public.company.id_company"), nullable=False
    )

    decision_type = db.Column(db.String(50), nullable=False)
    reasoning = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    feature = db.relationship("Features_ideas", back_populates="decisions")

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
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    sender = db.relationship("Profile")
    project = db.relationship("Project")
