from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json
import hashlib

# Create db instance FIRST
db = SQLAlchemy()

# Association table
volunteer_tasks = db.Table('volunteer_tasks',
    db.Column('volunteer_id', db.Integer, db.ForeignKey('volunteers.id')),
    db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'))
)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_id(self):
        return str(self.id)

class Family(db.Model):
    __tablename__ = 'families'
    id = db.Column(db.Integer, primary_key=True)
    family_code = db.Column(db.String(20), unique=True, nullable=False)
    head_name = db.Column(db.String(100), nullable=False)
    total_members = db.Column(db.Integer, default=1)
    children_count = db.Column(db.Integer, default=0)
    elderly_count = db.Column(db.Integer, default=0)
    disabled_count = db.Column(db.Integer, default=0)
    sick_count = db.Column(db.Integer, default=0)
    pregnant_count = db.Column(db.Integer, default=0)
    food_need = db.Column(db.Integer, default=2)
    water_need = db.Column(db.Integer, default=2)
    medicine_need = db.Column(db.Integer, default=2)
    shelter_need = db.Column(db.Integer, default=2)
    camp_zone = db.Column(db.String(10), default='A')
    tent_number = db.Column(db.String(20))
    priority_score = db.Column(db.Float, default=0)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def calculate_priority_score(self):
        vulnerability_points = (
            self.children_count * 2 +
            self.elderly_count * 3 +
            self.disabled_count * 4 +
            self.sick_count * 3 +
            self.pregnant_count * 2
        )
        need_points = self.food_need + self.water_need + self.medicine_need + self.shelter_need
        score = vulnerability_points + need_points
        size_factor = min(1.5, 1 + (self.total_members / 20))
        self.priority_score = round(score * size_factor, 2)
        return self.priority_score
    
    def get_vulnerability_level(self):
        if self.priority_score >= 15:
            return "Critical"
        elif self.priority_score >= 10:
            return "High"
        elif self.priority_score >= 5:
            return "Medium"
        else:
            return "Low"
    
    def to_dict(self):
        return {
            'id': self.id,
            'family_code': self.family_code,
            'head_name': self.head_name,
            'total_members': self.total_members,
            'children': self.children_count,
            'elderly': self.elderly_count,
            'disabled': self.disabled_count,
            'sick': self.sick_count,
            'pregnant': self.pregnant_count,
            'camp_zone': self.camp_zone,
            'tent_number': self.tent_number,
            'priority_score': self.priority_score,
            'vulnerability_level': self.get_vulnerability_level()
        }

class Resource(db.Model):
    __tablename__ = 'resources'
    id = db.Column(db.Integer, primary_key=True)
    resource_type = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20), default='units')
    expiry_date = db.Column(db.DateTime, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class Allocation(db.Model):
    __tablename__ = 'allocations'
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'))
    resource_type = db.Column(db.String(50))
    quantity = db.Column(db.Float)
    allocated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    priority_score_at_time = db.Column(db.Float)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Ledger(db.Model):
    __tablename__ = 'ledger'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'))
    resource_type = db.Column(db.String(50))
    quantity = db.Column(db.Float)
    action = db.Column(db.String(20))
    allocated_by = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    current_hash = db.Column(db.String(200), unique=True)

class Volunteer(db.Model):
    __tablename__ = 'volunteers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    skills = db.Column(db.String(200))
    assigned_zone = db.Column(db.String(10))
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(50))
    zone = db.Column(db.String(10))
    status = db.Column(db.String(20), default='pending')
    priority = db.Column(db.Integer, default=2)
    assigned_to = db.Column(db.Integer, db.ForeignKey('volunteers.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

class CampZone(db.Model):
    __tablename__ = 'camp_zones'
    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(10), unique=True)
    x_coord = db.Column(db.Float)
    y_coord = db.Column(db.Float)
    population = db.Column(db.Integer, default=0)

class Path(db.Model):
    __tablename__ = 'paths'
    id = db.Column(db.Integer, primary_key=True)
    from_zone = db.Column(db.String(10))
    to_zone = db.Column(db.String(10))
    distance = db.Column(db.Float)

class EmergencyRequest(db.Model):
    __tablename__ = 'emergency_requests'
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'))
    emergency_type = db.Column(db.String(50))
    severity = db.Column(db.Integer, default=2)
    status = db.Column(db.String(20), default='pending')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    family = db.relationship('Family', backref='emergencies')