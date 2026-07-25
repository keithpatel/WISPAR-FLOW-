"""
WISPAR FLOW - Voice Commands & Formatting Processor
Handles offline spoken punctuation, custom text macros, and local system actions.
"""

import re
import os
import time
import datetime
import subprocess
import ctypes
import win32clipboard

PUNCTUATION_RULES = [
    (r'\bnew paragraph\b', '\n\n'),
    (r'\bnew line\b', '\n'),
    (r'\bbullet point\b', '• '),
    (r'\bfull stop\b', '.'),
    (r'\bperiod\b', '.'),
    (r'\bcomma\b', ','),
    (r'\bquestion mark\b', '?'),
    (r'\bexclamation mark\b', '!'),
    (r'\bcolon\b', ':'),
    (r'\bsemicolon\b', ';'),
    (r'\bopen quote\b', '"'),
    (r'\bclose quote\b', '"'),
]

def send_key_combo(vk_code_list):
    """Simulate key press combinations using Windows API."""
    for vk in vk_code_list:
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.01)
    for vk in reversed(vk_code_list):
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.01)

class VoiceCommandProcessor:
    def __init__(self, config_manager=None):
        self.config = config_manager

    def process(self, text: str) -> tuple[str, bool]:
        """
        Process transcribed text for commands and macros.
        Returns: (processed_text, is_system_action)
        If is_system_action is True, processed_text is an informational log message.
        """
        if not text:
            return text, False

        text_clean = text.strip().lower().rstrip('.!')

        # 1. System Voice Hotkeys & Key Combos
        if text_clean in ["undo that", "scratch that"]:
            send_key_combo([0x11, 0x5A])  # Ctrl + Z
            return "[Action: Undo (Ctrl+Z)]", True

        elif text_clean in ["select all"]:
            send_key_combo([0x11, 0x41])  # Ctrl + A
            return "[Action: Select All (Ctrl+A)]", True

        elif text_clean in ["copy that"]:
            send_key_combo([0x11, 0x43])  # Ctrl + C
            return "[Action: Copy (Ctrl+C)]", True

        elif text_clean in ["paste that"]:
            send_key_combo([0x11, 0x56])  # Ctrl + V
            return "[Action: Paste (Ctrl+V)]", True

        elif text_clean in ["press enter", "hit enter"]:
            send_key_combo([0x0D])  # Enter
            return "[Action: Pressed Enter]", True

        elif text_clean in ["backspace", "delete character"]:
            send_key_combo([0x08])  # Backspace
            return "[Action: Pressed Backspace]", True

        elif text_clean in ["open notepad", "launch notepad"]:
            subprocess.Popen(["notepad.exe"])
            return "[Action: Opened Notepad]", True

        elif text_clean in ["open browser", "launch browser"]:
            os.system("start https://www.google.com")
            return "[Action: Opened Browser]", True

        elif text_clean in ["clear clipboard", "empty clipboard"]:
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.CloseClipboard()
            except:
                pass
            return "[Action: Cleared Clipboard]", True

        elif text_clean in ["lock computer", "lock pc"]:
            subprocess.run(["ctypes.windll.user32.LockWorkStation()"], shell=True)
            return "[Action: Locked PC]", True

        # 2. Custom User Macros & Replacements (with Dynamic Placeholders)
        if self.config:
            custom = self.config.get("custom_replacements", {})
            for key, val in custom.items():
                if key:
                    pattern = re.compile(rf'\b{re.escape(key)}\b', re.IGNORECASE)
                    if pattern.search(text):
                        val_replaced = self._expand_dynamic_placeholders(val)
                        text = pattern.sub(val_replaced, text)

        # 3. Punctuation Replacement
        if self.config is None or self.config.get("auto_punctuation", True):
            for pattern, replacement in PUNCTUATION_RULES:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Clean up double spaces around punctuation
        text = re.sub(r'\s+([.,?!:;])', r'\1', text)

        return text, False

    def _expand_dynamic_placeholders(self, text: str) -> str:
        """Replace dynamic tags like {date}, {time}, {clipboard}."""
        now = datetime.datetime.now()
        text = text.replace("{date}", now.strftime("%Y-%m-%d"))
        text = text.replace("{time}", now.strftime("%I:%M %p"))
        text = text.replace("{datetime}", now.strftime("%Y-%m-%d %H:%M:%S"))

        if "{clipboard}" in text:
            clip_text = ""
            try:
                win32clipboard.OpenClipboard()
                clip_text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except:
                clip_text = ""
            text = text.replace("{clipboard}", clip_text if clip_text else "")

        return text
