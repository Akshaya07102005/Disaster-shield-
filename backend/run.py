import os
import sys

# Ensure project root is in python search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env')))
load_dotenv()

from backend.app import create_app, socketio
import backend.app.sockets  # Ensures socket decorators are registered

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Disaster Shield AI Command Center Server launching at http://127.0.0.1:{port}")
    socketio.run(app, host='127.0.0.1', port=port, debug=True, allow_unsafe_werkzeug=True)
