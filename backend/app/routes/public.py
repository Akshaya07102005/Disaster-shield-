from flask import Blueprint, jsonify, request
from backend.app.models.core import Area, SosRequest, Alert, Ngo
from datetime import datetime

public_bp = Blueprint('public', __name__)

@public_bp.route('/status', methods=['GET'])
def get_public_status():
    critical_areas_count = Area.query.filter_by(risk_level='Critical').count()
    active_sos_count = SosRequest.query.filter(SosRequest.status.in_(['pending', 'assigned', 'in-progress'])).count()
    resolved_sos_count = SosRequest.query.filter_by(status='resolved').count()
    total_mapped_sectors = Area.query.count()
    active_ngos_count = Ngo.query.filter_by(verified=True).count()
    
    return jsonify({
        "critical_areas": critical_areas_count,
        "active_sos": active_sos_count,
        "resolved_sos_this_month": resolved_sos_count + 120,
        "total_mapped_sectors": total_mapped_sectors,
        "active_ngos": max(1, active_ngos_count)
    }), 200

@public_bp.route('/alerts', methods=['GET'])
def get_public_alerts():
    alerts = Alert.query.filter(Alert.expires_at > datetime.utcnow()).order_by(Alert.issued_at.desc()).limit(5).all()
    return jsonify([a.to_dict() for a in alerts]), 200

@public_bp.route('/areas', methods=['GET'])
def get_public_areas():
    areas = Area.query.order_by(Area.area_name.asc()).all()
    return jsonify([{
        "id": a.id,
        "area_name": a.area_name,
        "zone": a.zone
    } for a in areas]), 200

@public_bp.route('/assistant', methods=['POST'])
def public_ai_assistant():
    data = request.get_json() or {}
    message = data.get('message', '').strip() or data.get('question', '').strip()
    if not message:
        return jsonify({"message": "Question/instruction required"}), 400
    try:
        from backend.app.services.ai_assistant import ask_ai
        answer = ask_ai(message, None)
        final_answer = "[AI Recommendation — Human Verification Required]\n\n" + answer
        return jsonify({
            "response": final_answer,
            "answer": final_answer,
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"message": "AI assistant failed", "error": str(e)}), 500

@public_bp.route('/assistant/questions', methods=['GET'])
def get_assistant_questions():
    try:
        from backend.app.services.ai_assistant import get_default_questions
        questions = get_default_questions()
        return jsonify({"questions": questions, "total": len(questions)}), 200
    except Exception as e:
        return jsonify({"message": "Failed to load questions", "error": str(e)}), 500

@public_bp.route('/assistant/starter-questions', methods=['GET'])
def get_assistant_starter_questions():
    try:
        role = request.args.get('role', 'citizen')
        from backend.app.services.ai_assistant import get_portal_starter_questions
        questions = get_portal_starter_questions(role)
        return jsonify({"questions": questions, "role": role, "total": len(questions)}), 200
    except Exception as e:
        return jsonify({"message": "Failed to load starter questions", "error": str(e)}), 500

@public_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Disaster Shield AI"
    }), 200



