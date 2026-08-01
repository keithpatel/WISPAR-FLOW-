"""
WISPAR FLOW - Sound Effects Engine
Provides audio cues for recording start, stop, paste success, and actions.
"""

import threading
import winsound
import time

def play_start_sound():
    def _play():
        try:
            winsound.Beep(880, 80)   # A5 note
            winsound.Beep(1320, 100) # E6 note
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()

def play_stop_sound():
    def _play():
        try:
            winsound.Beep(1100, 80)
            winsound.Beep(700, 100)
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()

def play_success_sound():
    def _play():
        try:
            winsound.Beep(1046, 60) # C6
            winsound.Beep(1318, 60) # E6
            winsound.Beep(1568, 90) # G6
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()

def play_action_sound():
    def _play():
        try:
            winsound.Beep(1500, 120)
        except Exception:
            pass
    threading.Thread(target=_play, daemon=True).start()
