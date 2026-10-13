import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from backend.app.models.core import db
from backend.app.config import Config

# Initialize SocketIO globally
socketio = SocketIO(cors_allowed_origins="*", async_mode='gevent' if os.environ.get('USE_GEVENT') else 'threading')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure static directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'static'), exist_ok=True)

    # Initialize extensions
    CORS(app, supports_credentials=True)
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Database table verification notice: {e}")
    
    jwt = JWTManager(app)
    
    # Initialize socketio with app
    socketio.init_app(app)
    
    # Register blueprints
    from backend.app.routes.auth import auth_bp
    from backend.app.routes.government import gov_bp
    from backend.app.routes.citizen import citizen_bp
    from backend.app.routes.ngo import ngo_bp
    from backend.app.routes.public import public_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(gov_bp, url_prefix='/api/gov')
    app.register_blueprint(citizen_bp, url_prefix='/api/citizen')
    app.register_blueprint(ngo_bp, url_prefix='/api/ngo')
    app.register_blueprint(public_bp, url_prefix='/api/public')
    
    # Catch-all routes to serve static frontend and generated reports
    from flask import send_from_directory, jsonify, make_response
    
    @app.route('/static/reports/<path:filename>')
    def serve_generated_report(filename):
        upload_folder = app.config['UPLOAD_FOLDER']
        full_path = os.path.join(upload_folder, filename)
        if os.path.exists(full_path):
            resp = make_response(send_from_directory(upload_folder, filename, mimetype='application/pdf'))
            resp.headers['Content-Type'] = 'application/pdf'
            resp.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            return resp
        return jsonify({"message": "Report PDF file not found on server."}), 404

    @app.route('/health')
    def health_check():
        return jsonify({"status": "healthy", "service": "Disaster Shield AI"}), 200

    @app.route('/')
    def serve_index():
        frontend_dir = os.path.abspath(os.path.join(app.root_path, '..', '..', 'frontend'))
        return send_from_directory(frontend_dir, 'index.html')
        
    @app.route('/<path:path>')
    def serve_frontend(path):
        # Special check for static reports
        if path.startswith('static/reports/'):
            filename = path.replace('static/reports/', '', 1)
            upload_folder = app.config['UPLOAD_FOLDER']
            full_path = os.path.join(upload_folder, filename)
            if os.path.exists(full_path):
                resp = make_response(send_from_directory(upload_folder, filename, mimetype='application/pdf'))
                resp.headers['Content-Type'] = 'application/pdf'
                resp.headers['Content-Disposition'] = f'inline; filename="{filename}"'
                return resp
            return jsonify({"message": "Report PDF file not found on server."}), 404

        frontend_dir = os.path.abspath(os.path.join(app.root_path, '..', '..', 'frontend'))
        # If path looks like an API call, let it go to 404 instead of serving HTML
        if path.startswith('api/'):
            return jsonify({"message": "API endpoint not found"}), 404
        # Otherwise serve from frontend folder
        file_path = os.path.join(frontend_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(frontend_dir, path)
        # Default fallback
        # If the file is in a subdirectory (like government/index.html), search for it
        if '/' in path:
            parts = path.split('/')
            sub_dir = os.path.join(frontend_dir, *parts[:-1])
            file_name = parts[-1]
            if os.path.exists(os.path.join(sub_dir, file_name)):
                return send_from_directory(sub_dir, file_name)
        return send_from_directory(frontend_dir, 'index.html')

    @app.errorhandler(404)
    def handle_404(e):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify({"message": "Endpoint not found", "error": "Not Found"}), 404
        frontend_dir = os.path.abspath(os.path.join(app.root_path, '..', '..', 'frontend'))
        return send_from_directory(frontend_dir, 'index.html')

    @app.errorhandler(500)
    def handle_500(e):
        from flask import request
        if request.path.startswith('/api/'):
            return jsonify({"message": "Internal server error occurred", "error": str(e)}), 500
        return jsonify({"message": "An unexpected error occurred"}), 500
    
    return app
