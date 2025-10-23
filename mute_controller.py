import subprocess
import platform
import logging

logger = logging.getLogger(__name__)

class MuteController:
    def __init__(self):
        self.system = platform.system()
        self.is_muted = False
    
    def mute(self):
        if self.is_muted:
            return
        
        try:
            if self.system == 'Linux':
                subprocess.run(['amixer', 'set', 'Master', 'mute'], check=True)
            elif self.system == 'Darwin':  # macOS
                subprocess.run(['osascript', '-e', 'set volume output muted true'], check=True)
            elif self.system == 'Windows':
                subprocess.run(['nircmd.exe', 'mutesysvolume', '1'], check=True)
            
            self.is_muted = True
            logger.info("Audio muted")
        except Exception as e:
            logger.error(f"Failed to mute: {e}")
    
    def unmute(self):
        if not self.is_muted:
            return
        
        try:
            if self.system == 'Linux':
                subprocess.run(['amixer', 'set', 'Master', 'unmute'], check=True)
            elif self.system == 'Darwin':  # macOS
                subprocess.run(['osascript', '-e', 'set volume output muted false'], check=True)
            elif self.system == 'Windows':
                subprocess.run(['nircmd.exe', 'mutesysvolume', '0'], check=True)
            
            self.is_muted = False
            logger.info("Audio unmuted")
        except Exception as e:
            logger.error(f"Failed to unmute: {e}")
    
    def toggle(self):
        if self.is_muted:
            self.unmute()
        else:
            self.mute()