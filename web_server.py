import os
import glob
import time
import cv2
from flask import Flask, render_template, Response, send_from_directory, current_app
from flask_socketio import SocketIO
from config import CONFIG

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cat-motion-detector-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store recent motion events in memory
recent_events = []
MAX_EVENTS = 100


def add_event(event):
    """Add a motion event to the recent events list."""
    recent_events.insert(0, event)
    if len(recent_events) > MAX_EVENTS:
        recent_events.pop()


@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Route for MJPEG video stream."""
    # Get frame_producer from app config before creating generator
    frame_producer = current_app.config.get('FRAME_PRODUCER')
    
    if frame_producer is None:
        return "Frame producer not initialized", 503
    
    def generate():
        while True:
            # Get the current frame from the frame producer
            frame = frame_producer.get_frame()
            
            if frame is not None:
                try:
                    # Encode the frame as JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    
                    if ret:
                        frame_data = buffer.tobytes()
                        
                        # Yield the frame in MJPEG format
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                except Exception as e:
                    print(f"Error encoding frame: {e}")
            
            # Wait a bit before getting the next frame
            time.sleep(0.1)
    
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/frames/<filename>')
def serve_frame(filename):
    """Serve individual frame images."""
    frame_dir = CONFIG.get("FRAME_DIR", "frames")
    return send_from_directory(frame_dir, filename)


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('Client disconnected')


def emit_motion_event(event):
    """Emit a motion detection event to all connected clients."""
    # Add to recent events
    add_event(event)
    
    # Prepare event data for web clients
    web_event = {
        'timestamp': event['timestamp'],
        'frame_path': event['frame_path'],
        'image_url': f"/frames/{os.path.basename(event['frame_path'])}"
    }
    
    # Broadcast to all connected clients
    socketio.emit('motion_detected', web_event)


def get_recent_events():
    """Get the list of recent motion events."""
    return recent_events


if __name__ == '__main__':
    # This won't be used when integrated with main.py,
    # but useful for standalone testing
    socketio.run(
        app,
        host=CONFIG.get("WEB_HOST", "0.0.0.0"),
        port=CONFIG.get("WEB_PORT", 5000),
        debug=CONFIG.get("DEBUG", False)
    )
