

import requests
import json
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FingerprintClient:
    def __init__(self):
        self.endpoint = 'http://10.68.92.170:3340'
        self.timeout = 1
    
    def set_endpoint(self, endpoint):
        self.endpoint = endpoint
    
    def test_connection(self):
        try:
            #Below is my custom code
            url = "http://10.68.92.170:3340/api/v1/Streams"
            headers = {
                "accept": "application/json",
                "authorization": "Basic YWRtaW46"
            }

            response = requests.get(url, headers=headers)
            print(response.text)


            #Above is my custom code

            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def match_audio(self, audio_data):
        try:
            # Convert audio data to format expected by API
            # This is a simplified version - actual implementation would
            # format the audio properly for the soundfingerprinting.emy API
            
            payload = {
                'audio': audio_data.tolist() if isinstance(audio_data, np.ndarray) else audio_data,
                'sample_rate': 44100
            }
            
            response = requests.post(
                f"{self.endpoint}/match",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Match request failed: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning("Fingerprint match request timed out")
            return None
        except Exception as e:
            logger.error(f"Error matching audio: {e}")
            return None
    
    def add_fingerprint(self, audio_file, metadata):
        try:
            with open(audio_file, 'rb') as f:
                files = {'audio': f}
                data = {'metadata': json.dumps(metadata)}
                
                response = requests.post(
                    f"{self.endpoint}/add",
                    files=files,
                    data=data,
                    timeout=30
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error adding fingerprint: {e}")
            return False