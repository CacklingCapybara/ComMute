#!/usr/bin/env python3
"""
ComMute - Commercial Detection and Auto-Mute System
Detects commercials in live TV feed and mutes audio via IR blaster
"""

import cv2
import numpy as np
import subprocess
import time
import logging
from datetime import datetime
from collections import deque
import threading
import json
import os
import tempfile
from dejavu import Dejavu
from dejavu.logic.recognizer.file_recognizer import FileRecognizer
import wave
import struct

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/commute.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IRBlasterController:
    """Controls TV mute/unmute via IR blaster using LIRC"""
    
    def __init__(self, remote_name='tv', mute_button='KEY_MUTE'):
        self.remote_name = remote_name
        self.mute_button = mute_button
        self.is_muted = False
        
    def send_command(self, command):
        """Send IR command via LIRC"""
        try:
            result = subprocess.run(
                ['irsend', 'SEND_ONCE', self.remote_name, command],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                logger.info(f"IR command sent: {command}")
                return True
            else:
                logger.error(f"IR command failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error sending IR command: {e}")
            return False
    
    def mute(self):
        """Mute the TV"""
        if not self.is_muted:
            if self.send_command(self.mute_button):
                self.is_muted = True
                logger.info("TV MUTED")
                return True
        return False
    
    def unmute(self):
        """Unmute the TV"""
        if self.is_muted:
            if self.send_command(self.mute_button):
                self.is_muted = False
                logger.info("TV UNMUTED")
                return True
        return False


class CommercialDetector:
    """Detects commercials using multiple heuristics"""
    
    def __init__(self, config):
        self.config = config
        self.frame_buffer = deque(maxlen=30)  # 1 second at 30fps
        self.scene_change_threshold = config.get('scene_change_threshold', 0.3)
        self.volume_spike_threshold = config.get('volume_spike_threshold', 1.5)
        self.detection_confidence = 0.0
        self.commercial_probability = 0.0  # Current probability (0.0 - 1.0)
        self.commercial_start_time = None
        self.in_commercial = False
        
        # Scene change detection
        self.prev_frame = None
        self.scene_changes = deque(maxlen=30)
        
        # Rapid edit detection (commercials have more cuts)
        self.cut_rate_window = deque(maxlen=300)  # 10 second window
        
        # Audio fingerprinting
        self.audio_match_detected = False
        self.last_audio_match_time = 0
        
    def analyze_frame(self, frame):
        """Analyze video frame for commercial patterns"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Scene change detection
        if self.prev_frame is not None:
            diff = cv2.absdiff(gray, self.prev_frame)
            change_ratio = np.sum(diff > 30) / diff.size
            
            is_scene_change = change_ratio > self.scene_change_threshold
            self.scene_changes.append(1 if is_scene_change else 0)
            self.cut_rate_window.append(1 if is_scene_change else 0)
        
        self.prev_frame = gray.copy()
        
        # Calculate recent cut rate and probability
        cut_rate = 0.0
        if len(self.cut_rate_window) >= 150:  # 5 seconds
            recent_cuts = sum(list(self.cut_rate_window)[-150:])
            cut_rate = recent_cuts / 5.0  # cuts per second
            
            # Calculate commercial probability based on cut rate
            # Regular programming: 0.5-1.5 cuts/sec → low probability
            # Commercials: 2-4+ cuts/sec → high probability
            if cut_rate < 1.5:
                self.commercial_probability = 0.0
            elif cut_rate < 2.0:
                # Transition zone
                self.commercial_probability = (cut_rate - 1.5) / 0.5 * 0.5  # 0.0 to 0.5
            elif cut_rate < 3.0:
                # Likely commercial
                self.commercial_probability = 0.5 + (cut_rate - 2.0) / 1.0 * 0.3  # 0.5 to 0.8
            else:
                # Very likely commercial
                self.commercial_probability = min(0.8 + (cut_rate - 3.0) / 2.0 * 0.2, 1.0)  # 0.8 to 1.0
            
            # Commercials typically have 2-4+ cuts per second
            if cut_rate > 2.0:
                return True, cut_rate
        else:
            self.commercial_probability = 0.0
        
        return False, cut_rate
    
    def detect_black_frames(self, frame):
        """Detect black frames (often transition to/from commercials)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        
        # Very dark frame
        return mean_brightness < 15
    
    def is_commercial_likely(self):
        """Determine if current content is likely a commercial"""
        if len(self.scene_changes) < 30:
            return False
        
        # High scene change rate in last second
        recent_changes = sum(list(self.scene_changes)[-30:])
        
        # Check for recent audio fingerprint match
        current_time = time.time()
        audio_match_recent = (current_time - self.last_audio_match_time) < 10.0  # Within last 10 seconds
        
        # Commercials have rapid scene changes OR audio fingerprint match
        return recent_changes >= 3 or audio_match_recent
    
    def set_audio_match(self, match_confidence):
        """Called when audio fingerprint matches a known commercial"""
        self.audio_match_detected = True
        self.last_audio_match_time = time.time()
        # Boost probability significantly on audio match
        self.commercial_probability = max(self.commercial_probability, 0.9)
        logger.info(f"Audio fingerprint match detected! Confidence: {match_confidence}")


class AudioFingerprinter:
    """Handles audio fingerprinting using Dejavu"""
    
    def __init__(self, config):
        self.config = config
        self.enabled = config.get('audio_fingerprinting_enabled', True)
        
        if not self.enabled:
            logger.info("Audio fingerprinting disabled in config")
            return
        
        # Initialize Dejavu with database config
        db_config = {
            'type': 'sqlite',
            'database': config.get('fingerprint_db_path', '/app/data/dejavu.db')
        }
        
        try:
            self.djv = Dejavu(db_config)
            logger.info("Audio fingerprinting initialized with Dejavu")
        except Exception as e:
            logger.error(f"Failed to initialize Dejavu: {e}")
            self.enabled = False
            return
        
        self.audio_buffer = []
        self.sample_rate = 44100
        self.check_interval = config.get('audio_check_interval', 3)  # Check every 3 seconds
        self.last_check_time = 0
    
    def add_audio_sample(self, audio_data):
        """Add audio data to buffer for fingerprinting"""
        if not self.enabled:
            return
        
        self.audio_buffer.extend(audio_data)
        
        # Keep approximately 3 seconds of audio
        max_samples = self.sample_rate * self.check_interval
        if len(self.audio_buffer) > max_samples:
            self.audio_buffer = self.audio_buffer[-max_samples:]
    
    def check_for_match(self):
        """Check if current audio matches known commercial fingerprints"""
        if not self.enabled or not self.audio_buffer:
            return None
        
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return None
        
        self.last_check_time = current_time
        
        try:
            # Write audio buffer to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
                # Write WAV header and data
                with wave.open(tmp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.sample_rate)
                    
                    # Convert float samples to 16-bit PCM
                    audio_array = np.array(self.audio_buffer)
                    audio_array = np.clip(audio_array * 32767, -32768, 32767).astype(np.int16)
                    wav_file.writeframes(audio_array.tobytes())
            
            # Recognize audio
            results = self.djv.recognize(FileRecognizer, tmp_path)
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            if results and results.get('song_name'):
                confidence = results.get('input_confidence', 0)
                logger.info(f"Audio match found: {results['song_name']} (confidence: {confidence})")
                return {
                    'name': results['song_name'],
                    'confidence': confidence,
                    'offset': results.get('offset_seconds', 0)
                }
            
        except Exception as e:
            logger.error(f"Error checking audio fingerprint: {e}")
        
        return None
    
    def fingerprint_commercial(self, audio_file_path, commercial_name):
        """Add a new commercial audio file to the fingerprint database"""
        if not self.enabled:
            logger.warning("Cannot fingerprint: audio fingerprinting is disabled")
            return False
        
        try:
            self.djv.fingerprint_file(audio_file_path, commercial_name)
            logger.info(f"Fingerprinted commercial: {commercial_name}")
            return True
        except Exception as e:
            logger.error(f"Error fingerprinting file: {e}")
            return False


class ComMute:
    """Main application class"""
    
    def __init__(self, config_path='/app/config/config.json'):
        self.load_config(config_path)
        self.ir_controller = IRBlasterController(
            remote_name=self.config.get('remote_name', 'tv'),
            mute_button=self.config.get('mute_button', 'KEY_MUTE')
        )
        self.detector = CommercialDetector(self.config)
        self.audio_fingerprinter = AudioFingerprinter(self.config)
        self.running = False
        self.video_capture = None
        self.audio_process = None
        
        # Stats
        self.stats = {
            'commercials_detected': 0,
            'audio_matches': 0,
            'mute_commands_sent': 0,
            'unmute_commands_sent': 0,
            'start_time': datetime.now().isoformat(),
            'uptime_seconds': 0
        }
        
    def load_config(self, config_path):
        """Load configuration from JSON file"""
        default_config = {
            'video_device': '/dev/video0',
            'remote_name': 'tv',
            'mute_button': 'KEY_MUTE',
            'scene_change_threshold': 0.3,
            'volume_spike_threshold': 1.5,
            'min_commercial_duration': 5,  # seconds
            'detection_buffer': 2,  # seconds before muting
            'fps': 30,
            'audio_fingerprinting_enabled': True,
            'fingerprint_db_path': '/app/data/dejavu.db',
            'audio_check_interval': 3,
            'audio_device': 'hw:1,0'  # ALSA audio device for capture card
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.warning(f"Could not load config file: {e}. Using defaults.")
        
        self.config = default_config
    
    def initialize_video_capture(self):
        """Initialize video capture device"""
        video_device = self.config.get('video_device', '/dev/video0')
        
        logger.info(f"Initializing video capture from {video_device}")
        
        # Try direct device
        self.video_capture = cv2.VideoCapture(video_device)
        
        if not self.video_capture.isOpened():
            logger.error(f"Could not open video device: {video_device}")
            # Try alternate capture method
            try:
                self.video_capture = cv2.VideoCapture(0)
            except Exception as e:
                logger.error(f"Video capture initialization failed: {e}")
                return False
        
        # Set capture properties
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.video_capture.set(cv2.CAP_PROP_FPS, self.config.get('fps', 30))
        
        logger.info("Video capture initialized successfully")
        return True
    
    def start_audio_capture(self):
        """Start capturing audio from the capture device"""
        if not self.audio_fingerprinter.enabled:
            logger.info("Audio fingerprinting disabled, skipping audio capture")
            return
        
        audio_device = self.config.get('audio_device', 'hw:1,0')
        logger.info(f"Starting audio capture from {audio_device}")
        
        # Start ffmpeg to capture audio
        try:
            self.audio_process = subprocess.Popen([
                'ffmpeg',
                '-f', 'alsa',
                '-i', audio_device,
                '-ar', '44100',
                '-ac', '1',
                '-f', 's16le',
                '-'
            ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            # Start audio processing thread
            audio_thread = threading.Thread(target=self.process_audio, daemon=True)
            audio_thread.start()
            
            logger.info("Audio capture started successfully")
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            logger.warning("Continuing without audio fingerprinting")
    
    def process_audio(self):
        """Process audio stream and check for fingerprint matches"""
        sample_size = 2  # 16-bit audio = 2 bytes per sample
        chunk_size = 4096
        
        while self.running and self.audio_process:
            try:
                # Read audio data
                audio_data = self.audio_process.stdout.read(chunk_size * sample_size)
                if not audio_data:
                    break
                
                # Convert bytes to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Add to fingerprinter buffer
                self.audio_fingerprinter.add_audio_sample(audio_array)
                
                # Check for matches periodically
                match = self.audio_fingerprinter.check_for_match()
                if match:
                    self.detector.set_audio_match(match['confidence'])
                    self.stats['audio_matches'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing audio: {e}")
                time.sleep(1)
    
    def process_stream(self):
        """Main processing loop"""
        logger.info("Starting video stream processing")
        
        frame_count = 0
        commercial_frame_streak = 0
        min_commercial_frames = self.config.get('min_commercial_duration', 5) * self.config.get('fps', 30)
        last_probability_log = time.time()
        
        while self.running:
            ret, frame = self.video_capture.read()
            
            if not ret:
                logger.warning("Failed to read frame from capture device")
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # Analyze frame
            is_commercial, confidence = self.detector.analyze_frame(frame)
            
            # Log commercial probability every 1 second
            current_time = time.time()
            if current_time - last_probability_log >= 1.0:
                probability_pct = self.detector.commercial_probability * 100
                status = "COMMERCIAL" if self.detector.in_commercial else "PROGRAM"
                mute_status = "MUTED" if self.ir_controller.is_muted else "UNMUTED"
                audio_indicator = "🎵" if self.detector.audio_match_detected else ""
                logger.info(f"Commercial Probability: {probability_pct:.1f}% {audio_indicator}| Status: {status} | Audio: {mute_status}")
                last_probability_log = current_time
                
                # Reset audio match flag after display
                if self.detector.audio_match_detected:
                    self.detector.audio_match_detected = False
            
            if is_commercial or self.detector.is_commercial_likely():
                commercial_frame_streak += 1
                
                # If we've detected commercial patterns for sufficient duration
                if commercial_frame_streak >= min_commercial_frames:
                    if not self.detector.in_commercial:
                        logger.info(f"Commercial detected (confidence: {confidence:.2f})")
                        self.detector.in_commercial = True
                        self.detector.commercial_start_time = time.time()
                        self.stats['commercials_detected'] += 1
                        
                        # Mute the TV
                        if self.ir_controller.mute():
                            self.stats['mute_commands_sent'] += 1
            else:
                # Reset streak if not commercial
                if commercial_frame_streak > 0:
                    commercial_frame_streak = max(0, commercial_frame_streak - 2)
                
                # If we were in a commercial and now back to program
                if self.detector.in_commercial and commercial_frame_streak == 0:
                    duration = time.time() - self.detector.commercial_start_time
                    logger.info(f"Commercial ended (duration: {duration:.1f}s)")
                    self.detector.in_commercial = False
                    
                    # Unmute the TV
                    if self.ir_controller.unmute():
                        self.stats['unmute_commands_sent'] += 1
            
            # Log stats periodically
            if frame_count % (30 * 60) == 0:  # Every minute
                self.log_stats()
            
            # Small delay to prevent CPU overload
            time.sleep(0.001)
    
    def log_stats(self):
        """Log current statistics"""
        self.stats['uptime_seconds'] = (datetime.now() - datetime.fromisoformat(self.stats['start_time'])).total_seconds()
        logger.info(f"Stats: {json.dumps(self.stats, indent=2)}")
    
    def start(self):
        """Start the ComMute application"""
        logger.info("=== ComMute Starting ===")
        
        if not self.initialize_video_capture():
            logger.error("Failed to initialize video capture. Exiting.")
            return
        
        # Start audio capture in background thread
        self.start_audio_capture()
        
        self.running = True
        
        try:
            self.process_stream()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the ComMute application"""
        logger.info("=== ComMute Stopping ===")
        self.running = False
        
        # Stop audio capture
        if self.audio_process:
            try:
                self.audio_process.terminate()
                self.audio_process.wait(timeout=5)
            except:
                self.audio_process.kill()
        
        # Unmute TV if currently muted
        if self.ir_controller.is_muted:
            self.ir_controller.unmute()
        
        # Release video capture
        if self.video_capture:
            self.video_capture.release()
        
        # Log final stats
        self.log_stats()
        
        logger.info("ComMute stopped successfully")


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ComMute - Commercial Detection and Auto-Mute')
    parser.add_argument('--fingerprint', metavar='AUDIO_FILE', 
                       help='Fingerprint a commercial audio file')
    parser.add_argument('--name', metavar='COMMERCIAL_NAME',
                       help='Name for the commercial being fingerprinted')
    args = parser.parse_args()
    
    # Create necessary directories
    os.makedirs('/app/logs', exist_ok=True)
    os.makedirs('/app/config', exist_ok=True)
    os.makedirs('/app/data', exist_ok=True)
    
    # Handle fingerprinting mode
    if args.fingerprint:
        if not args.name:
            logger.error("--name is required when fingerprinting")
            return
        
        logger.info(f"Fingerprinting mode: {args.fingerprint} as '{args.name}'")
        config_path = '/app/config/config.json'
        
        # Load config
        default_config = {
            'audio_fingerprinting_enabled': True,
            'fingerprint_db_path': '/app/data/dejavu.db'
        }
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                default_config.update(json.load(f))
        
        # Initialize fingerprinter and add commercial
        fingerprinter = AudioFingerprinter(default_config)
        success = fingerprinter.fingerprint_commercial(args.fingerprint, args.name)
        
        if success:
            logger.info(f"Successfully fingerprinted: {args.name}")
        else:
            logger.error("Fingerprinting failed")
        return
    
    # Start ComMute
    app = ComMute()
    app.start()


if __name__ == '__main__':
    main()
