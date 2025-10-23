import requests
import json
import base64
import os
import logging
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

class FingerprintClient:
    def __init__(self):
        # Emy Docker container runs on port 3340
        self.endpoint = 'http://soundfingerprinting:3340/api/v1.1'
        self.timeout = 10
        # Default credentials for Community Edition
        self.auth = HTTPBasicAuth('Admin', '')
    
    def set_endpoint(self, endpoint):
        # Remove /api/v1.1 if provided, we'll add it
        self.endpoint = endpoint.rstrip('/api/v1.1').rstrip('/')
        self.endpoint = f"{self.endpoint}/api/v1.1"
    
    def test_connection(self):
        """Test connection by fetching tracks"""
        try:
            response = requests.get(
                f"{self.endpoint}/tracks",
                auth=self.auth,
                headers={'Accept': 'application/json'},
                timeout=self.timeout
            )
            logger.info(f"Connection test response: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def match_audio(self, audio_file_path):
        """
        Query Emy with an audio file to find matches
        Uses the GET /tracks endpoint with file parameter
        """
        try:
            if not os.path.exists(audio_file_path):
                logger.error(f"Audio file not found: {audio_file_path}")
                return None
            
            # Use multipart form to upload file for querying
            with open(audio_file_path, 'rb') as f:
                files = {'file': f}
                
                response = requests.post(
                    f"{self.endpoint}/tracks/query",
                    auth=self.auth,
                    files=files,
                    headers={'Accept': 'application/json'},
                    timeout=self.timeout
                )
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"Query response: {results}")
                
                # Check if we have matches
                if results and len(results) > 0:
                    # Return simplified match result
                    best_match = results[0]
                    audio_coverage = best_match.get('audio', {}).get('coverage', {})
                    
                    return {
                        'is_match': True,
                        'confidence': audio_coverage.get('trackCoverage', 0),
                        'track_id': best_match.get('track', {}).get('id'),
                        'track_title': best_match.get('track', {}).get('title'),
                        'duration': audio_coverage.get('trackCoverageLength', 30)
                    }
                else:
                    return {'is_match': False}
            else:
                logger.warning(f"Query failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning("Fingerprint query timed out")
            return None
        except Exception as e:
            logger.error(f"Error querying audio: {e}")
            return None
    
    def add_fingerprint(self, audio_file, track_id, title, artist='Unknown', media_type='Audio'):
        """
        Insert a track (commercial) into Emy for future matching
        Uses PUT /tracks endpoint
        """
        try:
            if not os.path.exists(audio_file):
                logger.error(f"Audio file not found: {audio_file}")
                return False
            
            # Prepare track metadata
            track_data = {
                'id': track_id,
                'title': title,
                'artist': artist,
                'mediaType': media_type
            }
            
            # Upload file with metadata
            with open(audio_file, 'rb') as f:
                files = {'file': (os.path.basename(audio_file), f, 'audio/wav')}
                
                # Add track metadata as form fields
                data = {
                    'track.id': track_data['id'],
                    'track.title': track_data['title'],
                    'track.artist': track_data['artist'],
                    'track.mediaType': track_data['mediaType'],
                    'insertOriginalPoints': 'true'
                }
                
                response = requests.post(
                    f"{self.endpoint}/tracks",
                    auth=self.auth,
                    files=files,
                    data=data,
                    headers={'Accept': 'application/json'},
                    timeout=30
                )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully added track: {title}")
                return True
            else:
                logger.error(f"Failed to add track: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding fingerprint: {e}")
            return False
    
    def get_matches(self, limit=50, since_days=1):
        """Retrieve registered matches from Emy"""
        try:
            response = requests.get(
                f"{self.endpoint}/matches",
                auth=self.auth,
                params={'limit': limit, 'sinceDays': since_days},
                headers={'Accept': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get matches: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting matches: {e}")
            return None