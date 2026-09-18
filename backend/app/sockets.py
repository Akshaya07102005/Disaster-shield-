from backend.app import socketio
from flask import request
from flask_socketio import join_room, leave_room

@socketio.on('connect')
def handle_connect():
    print(f"SocketIO client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"SocketIO client disconnected: {request.sid}")

@socketio.on('join_room')
@socketio.on('join')
def on_join(data):
    if isinstance(data, dict):
        room = data.get('room')
    elif isinstance(data, str):
        room = data
    else:
        room = None
        
    if room:
        join_room(room)
        print(f"Client {request.sid} joined room: {room}")

@socketio.on('leave_room')
def on_leave(data):
    if isinstance(data, dict):
        room = data.get('room')
    elif isinstance(data, str):
        room = data
    else:
        room = None
    if room:
        leave_room(room)
        print(f"Client {request.sid} left room: {room}")
