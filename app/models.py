from . import db  # haal db uit __init__.py

class Company(db.Model):
    __tablename__ = 'company'
    __table_args__ = {'schema': 'public'}

    id_company = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String, nullable=False)

    profiles = db.relationship('Profile', back_populates='company')


class Profile(db.Model):
    __tablename__ = 'profile'
    __table_args__ = {'schema': 'public'}

    id_profile = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    role = db.Column(db.String, nullable=True)
    id_company = db.Column(db.Integer, db.ForeignKey('public.company.id_company'))

    company = db.relationship('Company', back_populates='profiles')

    def __repr__(self):
        return f"<Profile {self.name}>"
