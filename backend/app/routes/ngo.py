from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app.models.core import db, User, Ngo, Mission, SosRequest, RescueTeam, Area, NgoCapacity, MissionMessage, AuditLog, SosStatusLog, Notification, NgoMember, Resource, Shelter
from backend.app.services.risk_engine import update_area_risk
from backend.app import socketio

ngo_bp = Blueprint('ngo', __name__)

def get_ngo_profile(identity):
    if not identity:
        return None
    user = User.query.get(int(identity))
    if not user or user.role != 'ngo':
        return None
    return Ngo.query.filter_by(user_id=user.id).first()

@ngo_bp.route('/missions', methods=['GET'])
@jwt_required()
def get_missions():
    identity = get_jwt_identity()
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "Access denied. NGO profile not found."}), 403
        
    missions = Mission.query.filter_by(ngo_id=ngo.id).all()
    return jsonify([m.to_dict() for m in missions]), 200

@ngo_bp.route('/missions/<int:mission_id>/accept', methods=['POST'])
@jwt_required()
def accept_mission(mission_id):
    identity = get_jwt_identity()
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "Access denied."}), 403
        
    mission = Mission.query.filter_by(id=mission_id, ngo_id=ngo.id).first()
    if not mission:
        return jsonify({"message": "Mission not found"}), 404
        
    try:
        mission.status = 'accepted'
        mission.sos_request.status = 'assigned'
        
        # Log status transition
        status_log = SosStatusLog(
            sos_request_id=mission.sos_request_id,
            old_status='assigned',
            new_status='accepted',
            changed_by=int(identity)
        )
        db.session.add(status_log)
        
        # Log audit trail
        audit = AuditLog(
            actor_id=int(identity),
            action_type="dispatch",
            target_type="Mission",
            target_id=mission.id,
            details_json=f"NGO accepted dispatch mission for SOS Request {mission.sos_request_id}."
        )
        db.session.add(audit)
        
        db.session.commit()
        
        # Broadcast mission update
        socketio.emit('sos_status_changed', {
            "sos_id": mission.sos_request_id,
            "status": "accepted",
            "mission": mission.to_dict()
        })
        
        # Seed notification for citizen
        if mission.sos_request and mission.sos_request.citizen_id:
            notif = Notification(
                user_id=mission.sos_request.citizen_id,
                title="Rescue Squad Assigned & Accepted",
                body=f"NGO '{ngo.org_name}' has accepted your SOS request #{mission.sos_request_id} and is preparing rescue deployment.",
                severity='info',
                read=False
            )
            db.session.add(notif)
            db.session.commit()
        
        return jsonify({"message": "Mission accepted", "mission": mission.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to accept mission", "error": str(e)}), 500

@ngo_bp.route('/missions/<int:mission_id>/status', methods=['PUT'])
@jwt_required()
def update_mission_status(mission_id):
    identity = get_jwt_identity()
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "Access denied."}), 403
        
    data = request.get_json() or {}
    new_status = data.get('status') # 'en-route', 'on-site', 'completed'
    
    if new_status not in ['accepted', 'en-route', 'on-site', 'completed']:
        return jsonify({"message": "Invalid mission status"}), 400
        
    mission = Mission.query.filter_by(id=mission_id, ngo_id=ngo.id).first()
    if not mission:
        return jsonify({"message": "Mission not found"}), 404
        
    try:
        sos = mission.sos_request
        old_sos_status = sos.status if sos else 'assigned'
        mission.status = new_status
        
        # Sync SOS status
        if sos:
            if new_status == 'completed':
                sos.status = 'resolved'
            else:
                sos.status = 'in-progress' if new_status == 'on-site' else 'assigned'
                
            # Log status transition
            status_log = SosStatusLog(
                sos_request_id=sos.id,
                old_status=old_sos_status,
                new_status=sos.status,
                changed_by=int(identity)
            )
            db.session.add(status_log)
        
        # Log Audit Trail
        audit = AuditLog(
            actor_id=int(identity),
            action_type="dispatch",
            target_type="Mission",
            target_id=mission.id,
            details_json=f"Mission status updated to '{new_status}' (SOS Request status resolved to '{sos.status if sos else 'unknown'}')."
        )
        db.session.add(audit)
        
        # Decrement NGO active mission count if completed
        if new_status == 'completed':
            cap = NgoCapacity.query.filter_by(ngo_id=ngo.id).first()
            if cap and cap.active_missions_count > 0:
                cap.active_missions_count -= 1
                
        # Seed notification for citizen
        if sos and sos.citizen_id:
            notif = Notification(
                user_id=sos.citizen_id,
                title=f"Rescue Status: {new_status.title()}",
                body=f"Rescue squad from '{ngo.org_name}' is now {new_status} for your SOS request #{sos.id}.",
                severity='critical' if new_status == 'completed' else 'high',
                read=False
            )
            db.session.add(notif)

        db.session.commit()
        
        # Recalculate area risk if resolved (SOS density decreased)
        if new_status == 'completed' and sos:
            update_area_risk(sos.area_id)
            
        # Broadcast status change via WebSockets
        socketio.emit('sos_status_changed', {
            "sos_id": sos.id if sos else mission.sos_request_id,
            "status": sos.status if sos else new_status,
            "mission": mission.to_dict()
        })
        
        return jsonify({"message": f"Mission status updated to {new_status}", "mission": mission.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to update mission status", "error": str(e)}), 500

@ngo_bp.route('/teams', methods=['GET', 'POST'])
@jwt_required()
def manage_teams():
    identity = get_jwt_identity()
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "Access denied."}), 403
        
    if request.method == 'GET':
        teams = RescueTeam.query.filter_by(ngo_id=ngo.id).all()
        return jsonify([t.to_dict() for t in teams]), 200
        
    if request.method == 'POST':
        data = request.get_json() or {}
        team_name = data.get('team_name')
        members_count = int(data.get('members_count', 5))
        
        if not team_name:
            return jsonify({"message": "Team name is required"}), 400
            
        try:
            team = RescueTeam(
                ngo_id=ngo.id,
                team_name=team_name,
                members_count=members_count,
                status='available'
            )
            db.session.add(team)
            db.session.commit()
            return jsonify({"message": "Rescue team created successfully", "team": team.to_dict()}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Failed to create rescue team", "error": str(e)}), 500

@ngo_bp.route('/teams/<int:team_id>/location', methods=['POST'])
@jwt_required()
def update_team_location(team_id):
    identity = get_jwt_identity()
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "Access denied."}), 403
        
    team = RescueTeam.query.filter_by(id=team_id, ngo_id=ngo.id).first()
    if not team:
        return jsonify({"message": "Rescue team not found"}), 404
        
    data = request.get_json() or {}
    lat = data.get('latitude')
    lng = data.get('longitude')
    status = data.get('status')
    
    if lat is None or lng is None:
        return jsonify({"message": "Latitude and longitude required"}), 400
        
    try:
        team.current_lat = lat
        team.current_lng = lng
        if status:
            team.status = status
            
        db.session.commit()
        
        # Broadcast live GPS position via WebSockets to everyone
        team_dict = team.to_dict()
        socketio.emit('team_location_update', team_dict)
        
        return jsonify({"message": "GPS coordinates transmitted successfully", "team": team_dict}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to transmit coordinates", "error": str(e)}), 500

@ngo_bp.route('/ai/recommend', methods=['POST'])
@jwt_required()
def recommend_resources():
    identity = get_jwt_identity()
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "Access denied."}), 403
        
    data = request.get_json() or {}
    sos_id = data.get('sos_id')
    
    if not sos_id:
        return jsonify({"message": "SOS request ID is required"}), 400
        
    sos = SosRequest.query.get(sos_id)
    if not sos:
        return jsonify({"message": "SOS request not found"}), 404
        
    # Smart recommendation engine logic based on severity
    people = sos.people_affected or 1
    med_needs = (sos.medical_needs or "").lower()
    desc = (sos.description or "").lower()
    
    # Calculate recommended size
    rec_members = 3
    rec_boats = 0
    supplies = "Standard medical kits and emergency rations."
    
    emergency_type_lower = sos.emergency_type.lower()
    if 'flood' in emergency_type_lower or 'trap' in emergency_type_lower:
        rec_boats = max(1, math.ceil(people / 4))
        rec_members = max(4, people + 1)
        supplies = f"Inflatable rescue boat, {people} life jackets, flashlights, high energy bars, dry blankets."
        
    if 'insulin' in med_needs or 'heart' in med_needs or 'bleeding' in med_needs or 'unconscious' in med_needs:
        rec_members = max(rec_members, 4)
        supplies += " Advanced Life Support (ALS) kit, portable oxygen cylinder, spine board, stretcher."
        
    return jsonify({
        "sos_id": sos.id,
        "recommended_team_size": rec_members,
        "recommended_boats": rec_boats,
        "critical_supplies": supplies,
        "rationale": f"Calculated based on {people} affected person(s) experiencing a {sos.emergency_type} emergency."
    }), 200

@ngo_bp.route('/capacity', methods=['GET'])
@jwt_required()
def get_ngo_capacity():
    identity = get_jwt_identity()
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "Access denied."}), 403
        
    try:
        cap = NgoCapacity.query.filter_by(ngo_id=ngo.id).first()
        if not cap:
            # Fallback
            cap = NgoCapacity(ngo_id=ngo.id, active_missions_count=0, max_concurrent_missions=5)
            db.session.add(cap)
            db.session.commit()
            
        return jsonify(cap.to_dict()), 200
    except Exception as e:
        return jsonify({"message": "Failed to fetch capacity status", "error": str(e)}), 500

@ngo_bp.route('/missions/<int:mission_id>/messages', methods=['GET', 'POST'])
@jwt_required()
def manage_mission_messages(mission_id):
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user:
        return jsonify({"message": "Access denied"}), 403
        
    mission = Mission.query.get(mission_id)
    if not mission:
        return jsonify({"message": "Mission not found"}), 404
        
    # Verify NGO or Government role can see messages
    if user.role == 'ngo':
        ngo = get_ngo_profile(identity)
        if not ngo or mission.ngo_id != ngo.id:
            return jsonify({"message": "Access denied"}), 403
    elif user.role != 'gov':
        return jsonify({"message": "Access denied"}), 403
        
    if request.method == 'GET':
        messages = MissionMessage.query.filter_by(mission_id=mission_id).order_by(MissionMessage.sent_at.asc()).all()
        return jsonify([m.to_dict() for m in messages]), 200
        
    if request.method == 'POST':
        data = request.get_json() or {}
        text = data.get('message')
        if not text:
            return jsonify({"message": "Message content is required"}), 400
            
        try:
            msg = MissionMessage(
                mission_id=mission_id,
                sender_id=user.id,
                message=text
            )
            db.session.add(msg)
            db.session.commit()
            
            # Broadcast live via WebSockets
            msg_dict = msg.to_dict()
            socketio.emit('new_mission_message', msg_dict)
            
            return jsonify(msg_dict), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Failed to send message", "error": str(e)}), 500

@ngo_bp.route('/missions/<int:mission_id>/route', methods=['GET'])
@jwt_required()
def get_mission_route_trail(mission_id):
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user:
        return jsonify({"message": "Access denied."}), 403
        
    mission = Mission.query.get(mission_id)
    if not mission:
        return jsonify({"message": "Mission not found"}), 404
        
    try:
        sos = mission.sos_request
        base_lat = 12.9802
        base_lng = 80.2228
        
        # 10 steps interpolation to represent simulated breadcrumbs trail
        route_trail = []
        for i in range(11):
            alpha = i / 10.0
            lat = base_lat + alpha * (sos.latitude - base_lat)
            lng = base_lng + alpha * (sos.longitude - base_lng)
            route_trail.append({"latitude": lat, "longitude": lng})
            
        return jsonify({
            "mission_id": mission_id,
            "route_trail": route_trail
        }), 200
    except Exception as e:
        return jsonify({"message": "Failed to calculate route", "error": str(e)}), 500

# ---------------- NGO Member Management (20,000 Scale Paginated Endpoint) ----------------
@ngo_bp.route('/members', methods=['GET'])
@jwt_required()
def get_ngo_members():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role not in ['ngo', 'gov']:
        return jsonify({"message": "Access denied"}), 403

    ngo_id = None
    if user.role == 'ngo':
        ngo = get_ngo_profile(identity)
        if not ngo:
            return jsonify({"message": "NGO profile not found"}), 404
        ngo_id = ngo.id
    else:
        ngo_id_param = request.args.get('ngo_id', type=int)
        if ngo_id_param:
            ngo_id = ngo_id_param

    query = NgoMember.query
    if ngo_id:
        query = query.filter_by(ngo_id=ngo_id)

    search = request.args.get('search')
    if search:
        query = query.filter(
            (NgoMember.name.like(f"%{search}%")) |
            (NgoMember.phone.like(f"%{search}%")) |
            (NgoMember.region.like(f"%{search}%"))
        )

    skill = request.args.get('skill')
    if skill:
        query = query.filter_by(skill=skill)

    availability = request.args.get('availability')
    if availability:
        query = query.filter_by(availability=availability)

    region = request.args.get('region')
    if region:
        query = query.filter_by(region=region)

    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'asc')
    
    col = getattr(NgoMember, sort_by, None)
    if not col:
        col = NgoMember.name
        
    if sort_order == 'desc':
        query = query.order_by(col.desc())
    else:
        query = query.order_by(col.asc())

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    limit = min(max(1, limit), 100)
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        "members": [m.to_dict() for m in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
        "limit": pagination.per_page
    }), 200

@ngo_bp.route('/members/assign', methods=['POST'])
@jwt_required()
def assign_members_team():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role != 'ngo':
        return jsonify({"message": "Access denied"}), 403
        
    ngo = get_ngo_profile(identity)
    if not ngo:
        return jsonify({"message": "NGO profile not found"}), 404

    data = request.get_json() or {}
    member_ids = data.get('member_ids', [])
    team_id = data.get('team_id')
    action = data.get('action') # 'assign', 'remove', 'offline'
    
    if not member_ids:
        return jsonify({"message": "No members specified"}), 400
        
    try:
        members = NgoMember.query.filter(NgoMember.id.in_(member_ids), NgoMember.ngo_id == ngo.id).all()
        team = RescueTeam.query.filter_by(id=team_id, ngo_id=ngo.id).first() if team_id else None
        
        for m in members:
            if action == 'assign' and team:
                m.availability = 'active'
                m.current_assignment = f"Rescue Team: {team.team_name}"
            elif action == 'remove':
                m.availability = 'available'
                m.current_assignment = None
            elif action == 'offline':
                m.availability = 'offline'
                m.current_assignment = None
                
        db.session.commit()
        return jsonify({"message": f"Successfully updated {len(members)} members status."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Assignment failed", "error": str(e)}), 500

# ---------------- NGO Disaster & Resource Analysis ----------------
@ngo_bp.route('/analysis/disasters', methods=['GET'])
@jwt_required()
def get_ngo_disaster_analysis():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role not in ['ngo', 'gov']:
        return jsonify({"message": "Access denied"}), 403
        
    try:
        soses = SosRequest.query.all()
        critical_count = sum(1 for s in soses if s.priority_score >= 25.0)
        high_count = sum(1 for s in soses if 15.0 <= s.priority_score < 25.0)
        med_count = sum(1 for s in soses if 5.0 <= s.priority_score < 15.0)
        low_count = sum(1 for s in soses if s.priority_score < 5.0)
        
        emergency_types = {}
        for s in soses:
            emergency_types[s.emergency_type] = emergency_types.get(s.emergency_type, 0) + 1

        return jsonify({
            "total_sos_requests": len(soses),
            "priority_breakdown": {
                "critical": critical_count,
                "high": high_count,
                "medium": med_count,
                "low": low_count
            },
            "types_breakdown": emergency_types
        }), 200
    except Exception as e:
        return jsonify({"message": "Analysis failed", "error": str(e)}), 500

@ngo_bp.route('/analysis/food', methods=['GET', 'POST'])
@jwt_required()
def get_ngo_food_analysis():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role not in ['ngo', 'gov']:
        return jsonify({"message": "Access denied"}), 403

    if request.method == 'GET':
        resources = Resource.query.filter_by(resource_type='food').all()
        total_avail = sum(r.quantity_available for r in resources)
        total_req = sum(r.quantity_required for r in resources)
        
        breakdown = [{
            "area_id": r.area_id,
            "area_name": r.area.area_name,
            "available": r.quantity_available,
            "required": r.quantity_required,
            "deficit": max(0, r.quantity_required - r.quantity_available)
        } for r in resources]
        
        return jsonify({
            "total_available_food_packets": total_avail,
            "total_required_food_packets": total_req,
            "breakdown": breakdown
        }), 200
        
    if request.method == 'POST':
        data = request.get_json() or {}
        area_id = data.get('area_id')
        qty_add = data.get('quantity_added', 0)
        qty_dist = data.get('quantity_distributed', 0)
        
        if not area_id:
            return jsonify({"message": "Area ID is required"}), 400
            
        try:
            res = Resource.query.filter_by(area_id=area_id, resource_type='food').first()
            if not res:
                res = Resource(area_id=area_id, resource_type='food', quantity_available=0, quantity_required=0)
                db.session.add(res)
                
            res.quantity_available = max(0, res.quantity_available + qty_add - qty_dist)
            res.quantity_required = max(0, res.quantity_required - qty_dist)
            
            db.session.commit()
            return jsonify(res.to_dict()), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"message": "Failed to update food levels", "error": str(e)}), 500

@ngo_bp.route('/analysis/shelters', methods=['GET'])
@jwt_required()
def get_ngo_shelter_analysis():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role not in ['ngo', 'gov']:
        return jsonify({"message": "Access denied"}), 403
        
    try:
        shelters = Shelter.query.all()
        total_capacity = sum(s.capacity for s in shelters)
        total_occupancy = sum(s.current_occupancy for s in shelters)
        
        return jsonify({
            "total_capacity": total_capacity,
            "total_occupancy": total_occupancy,
            "remaining_capacity": max(0, total_capacity - total_occupancy),
            "shelters": [s.to_dict() for s in shelters]
        }), 200
    except Exception as e:
        return jsonify({"message": "Shelter analysis failed", "error": str(e)}), 500

@ngo_bp.route('/ai/recommend-resources', methods=['POST'])
@jwt_required()
def get_ai_resource_recommendation():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role not in ['ngo', 'gov']:
        return jsonify({"message": "Access denied"}), 403

    data = request.get_json() or {}
    sos_id = data.get('sos_id')
    
    if not sos_id:
        return jsonify({"message": "SOS Request ID is required"}), 400
        
    sos = SosRequest.query.get(sos_id)
    if not sos:
        return jsonify({"message": "SOS request not found"}), 404
        
    try:
        score = sos.priority_score
        people = sos.people_affected
        
        if score >= 25.0:
            suggested_team_size = 10
            suggested_skills = ["rescue", "medical support", "transportation"]
            equipment = ["Inflatable Boat", "Life Jackets", "First Aid Trauma Kits", "VHF Radios"]
            food_qty = people * 6
            vehicles = "1 Rescue Truck + 1 Motorboat"
        elif score >= 15.0:
            suggested_team_size = 5
            suggested_skills = ["rescue", "food distribution"]
            equipment = ["Life Jackets", "First Aid Kits", "Ropes & Spotlights"]
            food_qty = people * 4
            vehicles = "1 SUV Response Vehicle"
        else:
            suggested_team_size = 3
            suggested_skills = ["logistics", "shelter management"]
            equipment = ["Basic First Aid Kit", "Dry Food Rations"]
            food_qty = people * 2
            vehicles = "1 Basic Utility Van"
            
        reasoning = f"Suggested response calibrated based on SOS priority score ({score}) with {people} affected citizens in the {sos.area.area_name} region."
        
        return jsonify({
            "sos_id": sos_id,
            "emergency_type": sos.emergency_type,
            "suggested_team_size": suggested_team_size,
            "suggested_skills": suggested_skills,
            "suggested_equipment": equipment,
            "suggested_food_water_pack": food_qty,
            "suggested_vehicles": vehicles,
            "reasoning": reasoning,
            "disclaimer": "AI Recommendation — Human Verification Required before finalizing dispatch vectors."
        }), 200
    except Exception as e:
        return jsonify({"message": "Recommendation analysis failed", "error": str(e)}), 500

@ngo_bp.route('/ai/assistant', methods=['POST'])
@jwt_required()
def ngo_ai_assistant():
    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or user.role not in ['ngo', 'gov']:
        return jsonify({"message": "Access denied"}), 403
        
    data = request.get_json() or {}
    message = data.get('message', '').strip() or data.get('question', '').strip()
    
    if not message:
        return jsonify({"message": "Question/instruction required"}), 400
        
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

@ngo_bp.route('/assistant', methods=['POST'])
@jwt_required()
def ngo_assistant_alias():
    return ngo_ai_assistant()



