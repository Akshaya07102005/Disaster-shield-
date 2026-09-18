from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.models.core import (
    db, User, Area, Alert, SosRequest, Shelter, Hospital, Mission, RescueTeam, Notification, FamilyGroup, SosStatusLog
)
from backend.app.services.sos_priority import calculate_sos_priority
from backend.app.services.risk_engine import update_area_risk
import math
from datetime import datetime
from backend.app import socketio

citizen_bp = Blueprint('citizen', __name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Computes great-circle distance between two GPS points in kilometers using Haversine formula.
    """
    R = 6371.0  # Earth's mean radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

def find_nearest_area(lat, lng):
    """
    Finds the closest Area from the database using Haversine distance.
    This resolves which of the 426 mapped sectors the GPS coordinate falls in.
    """
    areas = Area.query.all()
    min_dist = float('inf')
    closest_area = None
    
    for a in areas:
        dist = haversine_distance(lat, lng, a.latitude, a.longitude)
        if dist < min_dist:
            min_dist = dist
            closest_area = a
            
    return closest_area

@citizen_bp.route('/alerts', methods=['GET'])
@jwt_required()
def get_alerts():
    identity = get_jwt_identity()
    # Citizens can query alerts. We can filter by area if provided
    area_id = request.args.get('area_id')
    
    # Active alerts
    query = Alert.query.filter(Alert.expires_at > datetime.utcnow())
    if area_id:
        # Get city-wide alerts (area_id IS NULL) or specific area alert
        query = query.filter((Alert.area_id == area_id) | (Alert.area_id == None))
        
    alerts = query.order_by(Alert.issued_at.desc()).all()
    return jsonify([a.to_dict() for a in alerts]), 200

@citizen_bp.route('/risk/<int:area_id>', methods=['GET'])
@jwt_required()
def get_area_risk(area_id):
    area = Area.query.get(area_id)
    if not area:
        return jsonify({"message": "Area not found"}), 404
    return jsonify(area.to_dict()), 200

@citizen_bp.route('/shelters', methods=['GET'])
@jwt_required()
def get_shelters():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    
    shelters = Shelter.query.all()
    shelter_list = [s.to_dict() for s in shelters]
    
    if lat is not None and lng is not None:
        # Sort by real Haversine distance
        for s in shelter_list:
            dist = haversine_distance(lat, lng, s['latitude'], s['longitude'])
            s['distance'] = dist
            s['distance_km'] = dist
        shelter_list.sort(key=lambda x: x['distance'])
        
    return jsonify(shelter_list), 200

@citizen_bp.route('/hospitals', methods=['GET'])
@jwt_required()
def get_hospitals():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    
    hospitals = Hospital.query.all()
    hospital_list = [h.to_dict() for h in hospitals]
    
    if lat is not None and lng is not None:
        # Sort by real Haversine distance
        for h in hospital_list:
            dist = haversine_distance(lat, lng, h['latitude'], h['longitude'])
            h['distance'] = dist
            h['distance_km'] = dist
        hospital_list.sort(key=lambda x: x['distance'])
        
    return jsonify(hospital_list), 200

@citizen_bp.route('/sos', methods=['GET'])
@jwt_required()
def get_my_soses():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role != 'citizen':
        return jsonify({"message": "Access denied"}), 403
        
    soses = SosRequest.query.filter_by(citizen_id=user.id).order_by(SosRequest.created_at.desc()).all()
    return jsonify([s.to_dict() for s in soses]), 200

@citizen_bp.route('/sos', methods=['POST'])
@jwt_required()
def trigger_sos():
    identity = get_jwt_identity()
    user = User.query.get(int(identity)) if identity else None
    if not user or user.role != 'citizen':
        return jsonify({"message": "Only citizens can issue SOS requests"}), 403
        
    data = request.get_json() or {}
    lat = data.get('latitude')
    lng = data.get('longitude')
    emergency_type = data.get('emergency_type')
    people_affected = int(data.get('people_affected', 1))
    medical_needs = data.get('medical_needs')
    description = data.get('description')
    
    if lat is None or lng is None or not emergency_type:
        return jsonify({"message": "Location and emergency type are required"}), 400
        
    # Resolve area mapping
    area = find_nearest_area(lat, lng)
    if not area:
        return jsonify({"message": "Resolved location is outside supported regions"}), 400
        
    try:
        # Create SOS request
        sos = SosRequest(
            citizen_id=int(identity),
            area_id=area.id,
            latitude=lat,
            longitude=lng,
            emergency_type=emergency_type,
            people_affected=people_affected,
            medical_needs=medical_needs,
            description=description,
            status='pending',
            priority_score=0.0
        )
        db.session.add(sos)
        db.session.flush()
        
        # Calculate priority score
        sos.priority_score = calculate_sos_priority(sos)
        
        # Create initial status log
        init_log = SosStatusLog(
            sos_request_id=sos.id,
            old_status=None,
            new_status='pending',
            changed_by=int(identity)
        )
        db.session.add(init_log)
        
        # Seed persistent DB notifications for all Gov and NGO responders
        responders = User.query.filter(User.role.in_(['gov', 'ngo'])).all()
        for responder in responders:
            notif = Notification(
                user_id=responder.id,
                title=f"🚨 EMERGENCY SOS #{sos.id}: {emergency_type} in {area.area_name}",
                body=f"Priority Score: {sos.priority_score:.1f} | Headcount: {people_affected} | Medical: {medical_needs or 'None'} | Desc: {description or 'No extra details'}",
                severity='critical',
                read=False
            )
            db.session.add(notif)

        db.session.commit()
        
        # Dynamic risk recalculation (increase area risk slightly due to new active SOS)
        update_area_risk(area.id)
        
        # Broadcast real-time SocketIO push to all command centers and rooms
        sos_dict = sos.to_dict()
        socketio.emit('new_sos_request', sos_dict)
        socketio.emit('new_sos', sos_dict)
        socketio.emit('new_sos_request', sos_dict, room='government')
        socketio.emit('new_sos_request', sos_dict, room='ngo')
        socketio.emit('new_sos', sos_dict, room='government')
        socketio.emit('new_sos', sos_dict, room='ngo')
        
        return jsonify({"message": "SOS alert sent successfully. Dispatch team notified.", "sos": sos_dict}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to issue SOS alert", "error": str(e)}), 500
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to issue SOS alert", "error": str(e)}), 500

@citizen_bp.route('/sos/<int:sos_id>/track', methods=['GET'])
@jwt_required()
def track_sos_rescue(sos_id):
    identity = get_jwt_identity()
    sos = SosRequest.query.get(sos_id)
    if not sos:
        return jsonify({"message": "SOS request not found"}), 404
        
    # Verify owner
    if sos.citizen_id != int(identity):
        return jsonify({"message": "Access denied"}), 403
        
    # Fetch assigned mission details
    mission = Mission.query.filter_by(sos_request_id=sos.id).first()
    mission_data = None
    team_data = None
    
    if mission:
        mission_data = mission.to_dict()
        # Find active teams for the assigned NGO
        teams = RescueTeam.query.filter_by(ngo_id=mission.ngo_id).all()
        team_data = [t.to_dict() for t in teams]
        
    return jsonify({
        "sos": sos.to_dict(),
        "mission": mission_data,
        "active_rescue_teams": team_data
    }), 200

@citizen_bp.route('/family-group', methods=['GET', 'POST', 'PUT'])
@jwt_required()
def manage_family_group():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role != 'citizen':
        return jsonify({"message": "Access denied"}), 403
        
    if request.method == 'GET':
        members = FamilyGroup.query.filter_by(owner_citizen_id=user.id).all()
        return jsonify([m.to_dict() for m in members]), 200
        
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('member_name')
        phone = data.get('member_phone')
        status = data.get('status', 'unknown')
        
        if not name or not phone:
            return jsonify({"message": "Member name and phone required"}), 400
            
        try:
            m = FamilyGroup(
                owner_citizen_id=user.id,
                member_name=name,
                member_phone=phone,
                status=status
            )
            db.session.add(m)
            db.session.commit()
            return jsonify(m.to_dict()), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Failed to add member", "error": str(e)}), 500
            
    if request.method == 'PUT':
        data = request.get_json() or {}
        member_id = data.get('member_id')
        status = data.get('status')
        
        if not member_id or not status:
            return jsonify({"message": "Member ID and safety status required"}), 400
            
        m = FamilyGroup.query.filter_by(id=member_id, owner_citizen_id=user.id).first()
        if not m:
            return jsonify({"message": "Member not found in your family group"}), 404
            
        try:
            m.status = status
            db.session.commit()
            return jsonify(m.to_dict()), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Failed to update safety status", "error": str(e)}), 500

@citizen_bp.route('/sos/queue-offline', methods=['POST'])
@jwt_required()
def sync_offline_soses():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role != 'citizen':
        return jsonify({"message": "Access denied"}), 403
        
    data = request.get_json() or {}
    soses_list = data.get('soses', [])
    
    synced_count = 0
    try:
        for item in soses_list:
            lat = item.get('latitude')
            lng = item.get('longitude')
            emergency_type = item.get('emergency_type')
            people_affected = int(item.get('people_affected', 1))
            medical_needs = item.get('medical_needs')
            description = item.get('description')
            offline_time_str = item.get('created_at')
            
            if lat is None or lng is None or not emergency_type:
                continue
                
            area = find_nearest_area(lat, lng)
            if not area:
                continue
                
            # Parse time if possible
            created_at = datetime.utcnow()
            if offline_time_str:
                try:
                    # Strip Z or offsets to keep it simple, or use isoformat
                    clean_str = offline_time_str.split('.')[0].replace('Z', '')
                    created_at = datetime.fromisoformat(clean_str)
                except:
                    pass
            
            sos = SosRequest(
                citizen_id=user.id,
                area_id=area.id,
                latitude=lat,
                longitude=lng,
                emergency_type=emergency_type,
                people_affected=people_affected,
                medical_needs=medical_needs,
                description=description,
                status='pending',
                priority_score=0.0,
                created_at=created_at
            )
            db.session.add(sos)
            db.session.flush()
            
            # Recalculate priority
            sos.priority_score = calculate_sos_priority(sos)
            
            # Emit Socket.io events
            sos_dict = sos.to_dict()
            socketio.emit('new_sos_request', sos_dict)
            socketio.emit('new_sos', sos_dict)
            socketio.emit('new_sos_request', sos_dict, room='government')
            socketio.emit('new_sos_request', sos_dict, room='ngo')
            
            # Seed notifications for responders
            responders = User.query.filter(User.role.in_(['gov', 'ngo'])).all()
            for responder in responders:
                notif = Notification(
                    user_id=responder.id,
                    title=f"🚨 SYNCED OFFLINE SOS #{sos.id}: {emergency_type} in {area.area_name}",
                    body=f"Priority Score: {sos.priority_score:.1f} | Headcount: {people_affected} | Medical: {medical_needs or 'None'}",
                    severity='critical',
                    read=False
                )
                db.session.add(notif)
            
            # Seed standard status log change
            log = SosStatusLog(
                sos_request_id=sos.id,
                old_status=None,
                new_status='pending',
                changed_by=user.id,
                changed_at=created_at
            )
            db.session.add(log)
            synced_count += 1
            
        db.session.commit()
        return jsonify({
            "message": f"Successfully synchronized {synced_count} offline SOS reports.",
            "synchronized_count": synced_count
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Offline sync failed", "error": str(e)}), 500

@citizen_bp.route('/notifications', methods=['GET', 'PUT'])
@jwt_required()
def manage_notifications():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user:
        return jsonify({"message": "Access denied"}), 403
        
    if request.method == 'GET':
        notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
        return jsonify([n.to_dict() for n in notifications]), 200
        
    if request.method == 'PUT':
        data = request.get_json() or {}
        notif_id = data.get('notification_id')
        
        try:
            if notif_id:
                # Mark single notification as read
                n = Notification.query.filter_by(id=notif_id, user_id=user.id).first()
                if n:
                    n.read = True
            else:
                # Mark all as read
                Notification.query.filter_by(user_id=user.id, read=False).update({Notification.read: True})
                
            db.session.commit()
            return jsonify({"message": "Notifications updated successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Failed to update notification", "error": str(e)}), 500

@citizen_bp.route('/assistant', methods=['POST'])
@jwt_required(optional=True)
def citizen_ai_assistant():
    data = request.get_json() or {}
    message = data.get('message', '').strip() or data.get('question', '').strip()
    if not message:
        return jsonify({"message": "Question/instruction required"}), 400
        
    identity = get_jwt_identity()
    user = User.query.get(int(identity)) if identity else None
    
    try:
        from backend.app.services.ai_assistant import ask_ai
        answer = ask_ai(message, user)
        final_answer = "[AI Recommendation — Human Verification Required]\n\n" + answer
        return jsonify({
            "response": final_answer,
            "answer": final_answer,
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"message": "AI assistant failed", "error": str(e)}), 500


