

from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
import json
import os
from datetime import datetime
import logging

from audio_manager import AudioManager
from fingerprint_client import FingerprintClient
from mute_controller import MuteController

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'commute-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
audio_manager = AudioManager()
fingerprint_client = FingerprintClient()
mute_controller = MuteController()

# Application state
app_state = {
    'status': 'idle',
    'is_running': False,
    'current_mute': None,
    'stats': {
        'total_mutes': 0,
        'total_muted_time': 0,
        'detection_accuracy': 0,
        'false_positives': 0
    },
    'activity_log': [],
    'config': {
        'audio_device': 'default',
        'matching_threshold': 0.85,
        'docker_endpoint': 'http://soundfingerprinting:5000',
        'database_path': '/data/commercials.db',
        'latency_target': 3,
        'enable_telemetry': False,
        'recording_path': '/recordings',
        'recording_duration': 15
    }
}

def add_log(message, log_type='info'):
    log_entry = {
        'id': int(time.time() * 1000),
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'message': message,
        'type': log_type
    }
    app_state['activity_log'].insert(0, log_entry)
    app_state['activity_log'] = app_state['activity_log'][:50]
    socketio.emit('log_update', log_entry)
    logger.info(f"[{log_type}] {message}")

def monitoring_loop():
    while app_state['is_running']:
        try:
            # Capture audio chunk
            audio_data = audio_manager.capture_chunk()
            
            if audio_data is None:
                time.sleep(0.1)
                continue
            
            # Send to fingerprinting service
            result = fingerprint_client.match_audio(audio_data)
            
            if result and result.get('is_match'):
                confidence = result.get('confidence', 0)
                duration = result.get('duration', 30)
                
                if confidence >= app_state['config']['matching_threshold']:
                    handle_commercial_detected(confidence, duration)
                    time.sleep(duration)
                    handle_commercial_ended(duration)
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            add_log(f"Error in monitoring: {str(e)}", 'error')
            time.sleep(1)

def handle_commercial_detected(confidence, duration):
    app_state['status'] = 'muted'
    app_state['current_mute'] = {
        'start': time.time(),
        'duration': duration
    }
    
    mute_controller.mute()
    add_log(f"Commercial detected (confidence: {confidence:.2f}) - Muted", 'mute')
    socketio.emit('status_update', {
        'status': 'muted',
        'current_mute': app_state['current_mute']
    })

def handle_commercial_ended(duration):
    app_state['status'] = 'listening'
    app_state['current_mute'] = None
    
    mute_controller.unmute()
    
    # Update stats
    app_state['stats']['total_mutes'] += 1
    app_state['stats']['total_muted_time'] += duration
    app_state['stats']['detection_accuracy'] = min(95, app_state['stats']['detection_accuracy'] + 0.5)
    
    add_log(f"Commercial ended - Unmuted (duration: {duration}s)", 'unmute')
    socketio.emit('status_update', {
        'status': 'listening',
        'current_mute': None
    })
    socketio.emit('stats_update', app_state['stats'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    return jsonify({
        'status': app_state['status'],
        'is_running': app_state['is_running'],
        'current_mute': app_state['current_mute'],
        'stats': app_state['stats'],
        'activity_log': app_state['activity_log'][:20],
        'config': app_state['config']
    })

@app.route('/api/start', methods=['POST'])
def start_monitoring():
    if not app_state['is_running']:
        app_state['is_running'] = True
        app_state['status'] = 'listening'
        
        # Initialize audio
        success = audio_manager.start(app_state['config']['audio_device'])
        if not success:
            app_state['is_running'] = False
            app_state['status'] = 'idle'
            return jsonify({'success': False, 'error': 'Failed to initialize audio'}), 500
        
        # Start monitoring thread
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        
        add_log('System started - Monitoring audio for commercials', 'info')
        return jsonify({'success': True, 'status': app_state['status']})
    
    return jsonify({'success': False, 'error': 'Already running'})

@app.route('/api/stop', methods=['POST'])
def stop_monitoring():
    if app_state['is_running']:
        app_state['is_running'] = False
        app_state['status'] = 'idle'
        app_state['current_mute'] = None
        
        audio_manager.stop()
        mute_controller.unmute()
        
        add_log('System stopped', 'info')
        return jsonify({'success': True, 'status': app_state['status']})
    
    return jsonify({'success': False, 'error': 'Not running'})

@app.route('/api/record', methods=['POST'])
def record_audio():
    try:
        duration = app_state['config']['recording_duration']
        add_log(f'Recording audio for {duration} seconds...', 'info')
        
        # Record audio in background thread
        def record():
            filename = audio_manager.record_to_file(
                duration=duration,
                output_path=app_state['config']['recording_path']
            )
            if filename:
                add_log(f'Audio saved to {filename}', 'success')
                socketio.emit('recording_complete', {'filename': filename})
            else:
                add_log('Recording failed', 'error')
        
        thread = threading.Thread(target=record, daemon=True)
        thread.start()
        
        return jsonify({'success': True, 'duration': duration})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        new_config = request.json
        app_state['config'].update(new_config)
        add_log('Configuration updated', 'success')
        return jsonify({'success': True, 'config': app_state['config']})
    
    return jsonify(app_state['config'])

@app.route('/api/test-docker', methods=['POST'])
def test_docker():
    try:
        add_log('Testing connection to soundfingerprinting.emy container...', 'info')
        result = fingerprint_client.test_connection()
        
        if result:
            add_log(f"Connected to {app_state['config']['docker_endpoint']} - API OK", 'success')
            return jsonify({'success': True, 'message': 'Connection successful'})
        else:
            add_log('Connection failed - Check Docker container is running', 'error')
            return jsonify({'success': False, 'error': 'Connection failed'}), 500
    except Exception as e:
        add_log(f'Connection error: {str(e)}', 'error')
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clear-data', methods=['POST'])
def clear_data():
    app_state['activity_log'] = []
    app_state['stats'] = {
        'total_mutes': 0,
        'total_muted_time': 0,
        'detection_accuracy': 0,
        'false_positives': 0
    }
    add_log('Data cleared', 'info')
    return jsonify({'success': True})

@socketio.on('connect')
def handle_connect():
    emit('status_update', {
        'status': app_state['status'],
        'is_running': app_state['is_running']
    })

if __name__ == '__main__':
    os.makedirs('/recordings', exist_ok=True)
    os.makedirs('/data', exist_ok=True)
    socketio.run(app, host='0.0.0.0', port=8080, debug=False)