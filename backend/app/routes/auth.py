from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    set_access_cookies, unset_jwt_cookies
)
from backend.app.models.core import db, User, Ngo

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    role = data.get('role')  # 'gov', 'citizen', 'ngo'
    home_area_id = data.get('home_area_id')
    
    if not all([name, email, phone, password, role]):
        return jsonify({"message": "Missing required fields"}), 400
        
    if role not in ['gov', 'citizen', 'ngo']:
        return jsonify({"message": "Invalid role"}), 400

    if role == 'gov':
        return jsonify({"message": "Government accounts cannot be self-registered. Please contact your system administrator."}), 403
        
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 400
        
    if User.query.filter_by(phone=phone).first():
        return jsonify({"message": "Phone number already registered"}), 400

    try:
        user = User(name=name, email=email, phone=phone, role=role, home_area_id=home_area_id)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # To obtain user.id
        
        # If NGO, create NGO profile (unverified by default)
        if role == 'ngo':
            org_name = data.get('org_name')
            registration_number = data.get('registration_number')
            contact_info = data.get('contact_info', phone)
            capacity = int(data.get('capacity', 10))
            
            if not org_name or not registration_number:
                db.session.rollback()
                return jsonify({"message": "Missing NGO organization details"}), 400
                
            if Ngo.query.filter_by(registration_number=registration_number).first():
                db.session.rollback()
                return jsonify({"message": "Registration number already exists"}), 400
                
            ngo = Ngo(
                user_id=user.id,
                org_name=org_name,
                registration_number=registration_number,
                verified=False,  # Needs government approval
                contact_info=contact_info,
                capacity=capacity
            )
            db.session.add(ngo)
            
        db.session.commit()
        return jsonify({"message": "Registration successful", "user": user.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Registration failed", "error": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401
        
    # Check if NGO and verified
    ngo_details = None
    if user.role == 'ngo':
        ngo = Ngo.query.filter_by(user_id=user.id).first()
        if ngo:
            ngo_details = ngo.to_dict()
            if not ngo.verified:
                return jsonify({"message": "NGO account is pending admin approval"}), 403

    # Generate JWT token
    identity = str(user.id)
    access_token = create_access_token(identity=identity)
    
    response_body = {
        "message": "Login successful",
        "access_token": access_token,
        "user": user.to_dict()
    }
    if ngo_details:
        response_body["ngo"] = ngo_details
        
    response = jsonify(response_body)
    # Set cookies in response for secure authentication
    set_access_cookies(response, access_token)
    return response, 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = jsonify({"message": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required(optional=True)
def get_current_user():
    # Supports both cookies and authorization headers
    identity = get_jwt_identity()
    if not identity:
        return jsonify({"message": "Unauthorized"}), 401
        
    user = User.query.get(int(identity))
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    response_body = {"user": user.to_dict()}
    if user.role == 'ngo':
        ngo = Ngo.query.filter_by(user_id=user.id).first()
        if ngo:
            response_body["ngo"] = ngo.to_dict()
            
    return jsonify(response_body), 200
