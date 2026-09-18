import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'gov', 'citizen', 'ngo'
    home_area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    home_area = db.relationship('Area', backref=db.backref('citizens', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'home_area_id': self.home_area_id,
            'created_at': self.created_at.isoformat()
        }

class Area(db.Model):
    __tablename__ = 'areas'
    
    id = db.Column(db.Integer, primary_key=True)
    area_name = db.Column(db.String(100), nullable=False)
    zone = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    boundary_geojson = db.Column(db.Text, nullable=True)  # Store GeoJSON string
    population = db.Column(db.Integer, default=0)
    risk_level = db.Column(db.String(20), default='Low')  # Low, Medium, High, Critical
    risk_score = db.Column(db.Float, default=0.0)
    
    # Factors for Risk Score Engine
    elevation = db.Column(db.Float, default=10.0)  # meters
    water_distance = db.Column(db.Float, default=1000.0)  # meters
    hist_frequency = db.Column(db.Float, default=0.0)  # 0.0 to 1.0 index
    rainfall_intensity = db.Column(db.Float, default=0.0)  # mm/hr (current rainfall)
    
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        boundary = None
        if self.boundary_geojson:
            try:
                boundary = json.loads(self.boundary_geojson)
            except Exception:
                boundary = self.boundary_geojson
        return {
            'id': self.id,
            'area_name': self.area_name,
            'zone': self.zone,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'boundary_geojson': boundary,
            'population': self.population,
            'risk_level': self.risk_level,
            'risk_score': round(self.risk_score, 4),
            'elevation': self.elevation,
            'water_distance': self.water_distance,
            'hist_frequency': self.hist_frequency,
            'rainfall_intensity': self.rainfall_intensity,
            'last_updated': self.last_updated.isoformat()
        }

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    disaster_type = db.Column(db.String(50), nullable=False)  # Flood, Cyclone, Heatwave, etc.
    severity = db.Column(db.String(20), nullable=False)  # Moderate, Severe, Extreme
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=True)  # Nullable means City-wide
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_test_data = db.Column(db.Boolean, default=False)

    area = db.relationship('Area', backref=db.backref('alerts', lazy=True))
    issuer = db.relationship('User', backref=db.backref('alerts_issued', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'disaster_type': self.disaster_type,
            'severity': self.severity,
            'area_id': self.area_id,
            'area_name': self.area.area_name if self.area else 'City-Wide',
            'issued_by': self.issued_by,
            'issuer_name': self.issuer.name,
            'issued_at': self.issued_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_test_data': self.is_test_data
        }

class SosRequest(db.Model):
    __tablename__ = 'sos_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    emergency_type = db.Column(db.String(50), nullable=False)  # Flood, Fire, Medical, Trapped, etc.
    people_affected = db.Column(db.Integer, default=1)
    medical_needs = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, assigned, in-progress, resolved
    priority_score = db.Column(db.Float, default=0.0, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_test_data = db.Column(db.Boolean, default=False)

    citizen = db.relationship('User', backref=db.backref('sos_requests', lazy=True))
    area = db.relationship('Area', backref=db.backref('sos_requests', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'citizen_id': self.citizen_id,
            'citizen_name': self.citizen.name,
            'citizen_phone': self.citizen.phone,
            'area_id': self.area_id,
            'area_name': self.area.area_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'emergency_type': self.emergency_type,
            'people_affected': self.people_affected,
            'medical_needs': self.medical_needs,
            'description': self.description,
            'status': self.status,
            'priority_score': round(self.priority_score, 2),
            'created_at': self.created_at.isoformat(),
            'is_test_data': self.is_test_data
        }

class Ngo(db.Model):
    __tablename__ = 'ngos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    org_name = db.Column(db.String(100), nullable=False)
    registration_number = db.Column(db.String(50), unique=True, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    contact_info = db.Column(db.String(255), nullable=True)
    capacity = db.Column(db.Integer, default=10)  # capacity in terms of rescue teams or volunteers

    user = db.relationship('User', backref=db.backref('ngo_profile', uselist=False, lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'org_name': self.org_name,
            'registration_number': self.registration_number,
            'verified': self.verified,
            'contact_info': self.contact_info,
            'capacity': self.capacity
        }

class Mission(db.Model):
    __tablename__ = 'missions'
    
    id = db.Column(db.Integer, primary_key=True)
    sos_request_id = db.Column(db.Integer, db.ForeignKey('sos_requests.id'), nullable=False)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='assigned', index=True)  # assigned, accepted, en-route, on-site, completed
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_test_data = db.Column(db.Boolean, default=False)

    sos_request = db.relationship('SosRequest', backref=db.backref('missions', lazy=True))
    ngo = db.relationship('Ngo', backref=db.backref('missions', lazy=True))
    assigner = db.relationship('User', backref=db.backref('missions_assigned', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'sos_request_id': self.sos_request_id,
            'sos_details': self.sos_request.to_dict(),
            'ngo_id': self.ngo_id,
            'ngo_name': self.ngo.org_name,
            'assigned_by': self.assigned_by,
            'status': self.status,
            'assigned_at': self.assigned_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_test_data': self.is_test_data
        }

class RescueTeam(db.Model):
    __tablename__ = 'rescue_teams'
    
    id = db.Column(db.Integer, primary_key=True)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id'), nullable=False)
    team_name = db.Column(db.String(100), nullable=False)
    members_count = db.Column(db.Integer, default=5)
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), default='available')  # available, active, offline

    ngo = db.relationship('Ngo', backref=db.backref('teams', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'ngo_id': self.ngo_id,
            'ngo_name': self.ngo.org_name,
            'team_name': self.team_name,
            'members_count': self.members_count,
            'current_lat': self.current_lat,
            'current_lng': self.current_lng,
            'status': self.status
        }

class Resource(db.Model):
    __tablename__ = 'resources'
    
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)  # medical, food, boats, shelter, personnel
    quantity_available = db.Column(db.Integer, default=0)
    quantity_required = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    area = db.relationship('Area', backref=db.backref('resources', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'area_id': self.area_id,
            'area_name': self.area.area_name,
            'resource_type': self.resource_type,
            'quantity_available': self.quantity_available,
            'quantity_required': self.quantity_required,
            'updated_at': self.updated_at.isoformat()
        }

class Shelter(db.Model):
    __tablename__ = 'shelters'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, default=100)
    current_occupancy = db.Column(db.Integer, default=0)
    contact = db.Column(db.String(50), nullable=True)

    area = db.relationship('Area', backref=db.backref('shelters', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'area_id': self.area_id,
            'area_name': self.area.area_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'capacity': self.capacity,
            'current_occupancy': self.current_occupancy,
            'contact': self.contact
        }

class Hospital(db.Model):
    __tablename__ = 'hospitals'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    contact = db.Column(db.String(50), nullable=True)
    beds_available = db.Column(db.Integer, default=10)

    area = db.relationship('Area', backref=db.backref('hospitals', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'area_id': self.area_id,
            'area_name': self.area.area_name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'contact': self.contact,
            'beds_available': self.beds_available
        }

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=True)
    report_type = db.Column(db.String(50), nullable=False)  # incident_summary, resource_needs, area_risk
    file_path = db.Column(db.String(255), nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    generator = db.relationship('User', backref=db.backref('reports_generated', lazy=True))
    area = db.relationship('Area', backref=db.backref('reports', lazy=True))

    def to_dict(self):
        filename = os.path.basename(self.file_path) if self.file_path else ''
        return {
            'id': self.id,
            'generated_by': self.generated_by,
            'generated_by_name': self.generator.name if self.generator else 'System',
            'area_id': self.area_id,
            'area_name': self.area.area_name if self.area else 'City-Wide',
            'report_type': self.report_type,
            'file_path': self.file_path,
            'filepath': self.file_path,
            'filename': filename,
            'generated_at': self.generated_at.isoformat()
        }

class AiQueryLog(db.Model):
    __tablename__ = 'ai_query_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('ai_queries', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name,
            'question': self.question,
            'answer': self.answer,
            'created_at': self.created_at.isoformat()
        }

class SosStatusLog(db.Model):
    __tablename__ = 'sos_status_logs'
    id = db.Column(db.Integer, primary_key=True)
    sos_request_id = db.Column(db.Integer, db.ForeignKey('sos_requests.id'), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    sos_request = db.relationship('SosRequest', backref=db.backref('status_logs', lazy=True))
    changer = db.relationship('User', backref=db.backref('status_logs_changed', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'sos_request_id': self.sos_request_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by,
            'changed_by_name': self.changer.name if self.changer else 'System',
            'changed_at': self.changed_at.isoformat()
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)  # dispatch, alert, resource_allocate, ngo_verify
    target_type = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.Integer, nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    actor = db.relationship('User', backref=db.backref('audit_actions', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'actor_id': self.actor_id,
            'actor_name': self.actor.name if self.actor else 'System',
            'action_type': self.action_type,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details_json,
            'created_at': self.created_at.isoformat()
        }

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    body = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='info')  # info, high, critical
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'body': self.body,
            'severity': self.severity,
            'read': self.read,
            'created_at': self.created_at.isoformat()
        }

class NgoCapacity(db.Model):
    __tablename__ = 'ngo_capacities'
    id = db.Column(db.Integer, primary_key=True)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id'), unique=True, nullable=False)
    active_missions_count = db.Column(db.Integer, default=0)
    max_concurrent_missions = db.Column(db.Integer, default=5)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ngo = db.relationship('Ngo', backref=db.backref('capacity_details', uselist=False, lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'ngo_id': self.ngo_id,
            'ngo_name': self.ngo.org_name if self.ngo else 'Unknown NGO',
            'active_missions_count': self.active_missions_count,
            'max_concurrent_missions': self.max_concurrent_missions,
            'updated_at': self.updated_at.isoformat()
        }

class FamilyGroup(db.Model):
    __tablename__ = 'family_groups'
    id = db.Column(db.Integer, primary_key=True)
    owner_citizen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member_name = db.Column(db.String(100), nullable=False)
    member_phone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='unknown')  # safe, unknown, needs_help
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', backref=db.backref('family_members', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'owner_citizen_id': self.owner_citizen_id,
            'member_name': self.member_name,
            'member_phone': self.member_phone,
            'status': self.status,
            'updated_at': self.updated_at.isoformat()
        }

class MissionMessage(db.Model):
    __tablename__ = 'mission_messages'
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('missions.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    mission = db.relationship('Mission', backref=db.backref('messages', lazy=True))
    sender = db.relationship('User', backref=db.backref('messages_sent', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'mission_id': self.mission_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender.name if self.sender else 'System',
            'sender_role': self.sender.role if self.sender else 'system',
            'message': self.message,
            'sent_at': self.sent_at.isoformat()
        }

class AreaWeatherLog(db.Model):
    __tablename__ = 'area_weather_logs'
    id = db.Column(db.Integer, primary_key=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False)
    temperature = db.Column(db.Float, default=30.0)
    rainfall_mm = db.Column(db.Float, default=0.0)
    humidity = db.Column(db.Float, default=60.0)
    wind_speed = db.Column(db.Float, default=10.0)
    weather_condition_level = db.Column(db.String(20), default='Low')  # Low, Moderate, Severe, Extreme
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

    area = db.relationship('Area', backref=db.backref('weather_logs', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'area_id': self.area_id,
            'area_name': self.area.area_name if self.area else 'Unknown',
            'temperature': self.temperature,
            'rainfall_mm': self.rainfall_mm,
            'humidity': self.humidity,
            'wind_speed': self.wind_speed,
            'weather_condition_level': self.weather_condition_level,
            'analyzed_at': self.analyzed_at.isoformat()
        }

class WeatherReport(db.Model):
    __tablename__ = 'weather_reports'
    id = db.Column(db.Integer, primary_key=True)
    generated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    summary_text = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255), nullable=False)
    area_count = db.Column(db.Integer, default=426)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    generator = db.relationship('User', backref=db.backref('weather_reports_generated', lazy=True))

    def to_dict(self):
        filename = os.path.basename(self.file_path) if self.file_path else ''
        return {
            'id': self.id,
            'generated_by': self.generated_by,
            'generated_by_name': self.generator.name if self.generator else 'System',
            'summary_text': self.summary_text,
            'file_path': self.file_path,
            'filepath': self.file_path,
            'filename': filename,
            'area_count': self.area_count,
            'generated_at': self.generated_at.isoformat()
        }

class NgoMember(db.Model):
    __tablename__ = 'ngo_members'
    
    id = db.Column(db.Integer, primary_key=True)
    ngo_id = db.Column(db.Integer, db.ForeignKey('ngos.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    region = db.Column(db.String(100), nullable=False, index=True)
    skill = db.Column(db.String(50), nullable=False, index=True)  # rescue, food distribution, medical support, shelter management, transportation, communication, logistics, disaster response
    availability = db.Column(db.String(20), default='available', index=True)  # available, active, offline
    current_assignment = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ngo = db.relationship('Ngo', backref=db.backref('members', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'ngo_id': self.ngo_id,
            'ngo_name': self.ngo.org_name if self.ngo else 'Unknown NGO',
            'name': self.name,
            'age': self.age,
            'phone': self.phone,
            'region': self.region,
            'skill': self.skill,
            'availability': self.availability,
            'current_assignment': self.current_assignment,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }


