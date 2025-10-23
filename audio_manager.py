

import pyaudio
import wave
import numpy as np
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class AudioManager:
    def __init__(self):
        self.pyaudio = None
        self.stream = None
        self.format = pyaudio.paInt16
        self.channels = 2
        self.rate = 44100
        self.chunk = 1024
        self.is_active = False
        
    def start(self, device_name='default'):
        try:
            self.pyaudio = pyaudio.PyAudio()
            
            # Find device index
            device_index = None
            if device_name == 'default':
                device_index = self.pyaudio.get_default_input_device_info()['index']
            else:
                for i in range(self.pyaudio.get_device_count()):
                    info = self.pyaudio.get_device_info_by_index(i)
                    if device_name.lower() in info['name'].lower():
                        device_index = i
                        break
            
            if device_index is None:
                device_index = self.pyaudio.get_default_input_device_info()['index']
            
            # Open stream
            self.stream = self.pyaudio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )
            
            self.is_active = True
            logger.info(f"Audio stream started on device {device_index}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start audio: {e}")
            return False
    
    def stop(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pyaudio:
            self.pyaudio.terminate()
        self.is_active = False
        logger.info("Audio stream stopped")
    
    def capture_chunk(self):
        if not self.is_active or not self.stream:
            return None
        
        try:
            data = self.stream.read(self.chunk, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.int16)
            return audio_array
        except Exception as e:
            logger.error(f"Error capturing audio: {e}")
            return None
    
    def record_to_file(self, duration=15, output_path='/recordings'):
        os.makedirs(output_path, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(output_path, f'recording_{timestamp}.wav')
        
        try:
            # Temporarily create recording stream
            p = pyaudio.PyAudio()
            stream = p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk
            )
            
            logger.info(f"Recording {duration} seconds of audio...")
            frames = []
            
            for _ in range(0, int(self.rate / self.chunk * duration)):
                data = stream.read(self.chunk, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Save to WAV file
            wf = wave.open(filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            logger.info(f"Recording saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return None
