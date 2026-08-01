"""
WISPAR FLOW v2.0 - Local Offline Voice Dictation for Windows
Press Ctrl+Shift+Space to start/stop recording and paste transcribed text anywhere.
100% Local & Free - Zero Paid APIs.
"""

import os
import sys
import time
import wave
import threading
import tempfile
import warnings
import traceback
import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import pystray
from PIL import Image, ImageDraw, ImageFont

# Import WISPAR FLOW v2.0 Modules
from config import ConfigManager
from voice_commands import VoiceCommandProcessor
from text_cleaner import TextCleaner
from history_manager import HistoryManager
from hud_overlay import HUDOverlay
from gui_app import ControlPanelGUI
from window_tracker import get_recommended_mode
import sound_effects

warnings.filterwarnings("ignore")

# ==============================================================================
# LOGGING & PATHS
# ==============================================================================

LOG_FILE = None

def log(msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    global LOG_FILE
    if LOG_FILE is None:
        log_dir = Path(__file__).parent.parent if '__file__' in dir() else Path.cwd()
        LOG_FILE = open(log_dir / "wispar_flow.log", "a", encoding="utf-8")
    LOG_FILE.write(line + "\n")
    LOG_FILE.flush()

def log_error(msg):
    log(f"ERROR: {msg}")
    log(traceback.format_exc())

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.float32
BLOCK_SIZE = 1024
APP_NAME = "WISPAR FLOW"
APP_VERSION = "2.0.0"

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.resolve()

MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

# ==============================================================================
# WINDOWS API WRAPPERS
# ==============================================================================

import win32clipboard
import win32con
import win32api
import win32gui
import ctypes
from ctypes import wintypes

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_SPACE = 0x20

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ('wVk', wintypes.WORD),
        ('wScan', wintypes.WORD),
        ('dwFlags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_ulong),
    ]

class _INPUT(ctypes.Structure):
    _fields_ = [
        ('type', wintypes.DWORD),
        ('ki', KEYBDINPUT),
    ]

def send_key(vk_code, press=True):
    flags = 0 if press else KEYEVENTF_KEYUP
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=flags, time=0, dwExtraInfo=ctypes.c_ulong(0))
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

# ==============================================================================
# GLOBAL HOTKEY
# ==============================================================================

WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_ALT = 0x0001
MOD_NOREPEAT = 0x4000

HOTKEY_ID = 9001
hwnd_hotkey = None

def hotkey_thread_func():
    global hwnd_hotkey
    def wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_HOTKEY and wparam == HOTKEY_ID:
            mode = state.config.get("hotkey_mode", "toggle")
            if mode == "push_to_talk":
                if not state.recording:
                    threading.Thread(target=toggle_dictation, daemon=True).start()
            else:
                threading.Thread(target=toggle_dictation, daemon=True).start()
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    wc = win32gui.WNDCLASS()
    wc.lpfnWndProc = wndproc
    wc.lpszClassName = "WisparFlowHotkeyWindow"
    wc.hInstance = win32api.GetModuleHandle(None)
    class_atom = win32gui.RegisterClass(wc)

    hwnd_hotkey = win32gui.CreateWindow(
        class_atom, "WisparFlowHotkey", 0, 0, 0, 0, 0,
        0, 0, wc.hInstance, None
    )

    result = ctypes.windll.user32.RegisterHotKey(hwnd_hotkey, HOTKEY_ID, MOD_CONTROL | MOD_SHIFT, VK_SPACE)
    if not result:
        log("ERROR: Failed to register hotkey (another app may be using Ctrl+Shift+Space)")
        return
    log("Hotkey registered: Ctrl+Shift+Space")

    # Keyup monitoring thread for push_to_talk release
    def ptt_keyup_monitor():
        while True:
            time.sleep(0.05)
            if state.recording and state.config.get("hotkey_mode", "toggle") == "push_to_talk":
                # Check if Space or Ctrl or Shift are released
                space_down = (ctypes.windll.user32.GetAsyncKeyState(VK_SPACE) & 0x8000) != 0
                ctrl_down = (ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
                shift_down = (ctypes.windll.user32.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
                if not (space_down and ctrl_down and shift_down):
                    # Key released in Push-To-Talk mode -> Stop recording
                    threading.Thread(target=toggle_dictation, daemon=True).start()

    threading.Thread(target=ptt_keyup_monitor, daemon=True).start()

    msg = wintypes.MSG()
    while True:
        ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
        if ret == 0:
            break
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

def stop_hotkey():
    global hwnd_hotkey
    if hwnd_hotkey:
        ctypes.windll.user32.UnregisterHotKey(hwnd_hotkey, HOTKEY_ID)
        win32gui.DestroyWindow(hwnd_hotkey)
        hwnd_hotkey = None

# ==============================================================================
# VOICE ACTIVITY DETECTION
# ==============================================================================

class VoiceActivityDetector:
    def __init__(self, threshold=0.008, min_speech_ms=300, min_silence_ms=500, sample_rate=16000):
        self.threshold = threshold
        self.min_speech_samples = int(min_speech_ms * sample_rate / 1000)
        self.min_silence_samples = int(min_silence_ms * sample_rate / 1000)
        self.sample_rate = sample_rate

    def is_speech(self, audio_chunk):
        energy = np.sqrt(np.mean(audio_chunk**2))
        return energy > self.threshold

    def extract_speech(self, audio):
        frame_length = int(0.02 * self.sample_rate)
        if len(audio) < frame_length:
            return audio
        is_speech = False
        speech_start = 0
        silence_count = 0
        speech_segments = []
        for i in range(0, len(audio) - frame_length + 1, frame_length):
            frame = audio[i:i + frame_length]
            speech_detected = self.is_speech(frame)
            if speech_detected and not is_speech:
                is_speech = True
                speech_start = max(0, i - int(0.2 * self.sample_rate))
                silence_count = 0
            elif not speech_detected and is_speech:
                silence_count += len(frame)
                if silence_count > self.min_silence_samples:
                    speech_end = min(len(audio), i + int(0.1 * self.sample_rate))
                    speech_segments.append(audio[speech_start:speech_end])
                    is_speech = False
                    silence_count = 0
        if is_speech:
            speech_segments.append(audio[speech_start:])
        if not speech_segments:
            return audio
        return np.concatenate(speech_segments)

# ==============================================================================
# STATE & APP MANAGERS
# ==============================================================================

class Status:
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"

class AppState:
    def __init__(self):
        self.status = Status.IDLE
        self.recording = False
        self.audio_buffer = []
        self.model = None
        self.tray_icon = None
        self.stream = None
        self.transcribed_count = 0
        self.last_toggle = 0
        self.recording_started_at = 0

        # Initialize Managers
        self.config = ConfigManager(BASE_DIR)
        self.voice_cmd = VoiceCommandProcessor(self.config)
        self.cleaner = TextCleaner(self.config)
        self.history = HistoryManager(BASE_DIR)
        self.hud = HUDOverlay(self.config)
        self.gui = ControlPanelGUI(self.config, self.history, self.reload_whisper_model)
        self.vad = VoiceActivityDetector(threshold=self.config.get("vad_threshold", 0.008))

    def set_status(self, status):
        self.status = status
        self.hud.set_status(status)
        if self.tray_icon:
            try:
                self.tray_icon.icon = create_icon(status)
                self.tray_icon.menu = create_menu()
                self.tray_icon.update_menu()
            except:
                pass

    def reload_whisper_model(self, new_model_size):
        log(f"Reloading Whisper model to '{new_model_size}'...")
        try:
            self.model = load_whisper_model(new_model_size)
            self.config.set("model_size", new_model_size)
            log("Whisper model reloaded successfully!")
        except Exception as e:
            log_error(f"Failed to reload model: {e}")

state = AppState()

# ==============================================================================
# AUDIO PIPELINE
# ==============================================================================

def audio_callback(indata, frames, time_info, status_msg):
    if state.recording:
        state.audio_buffer.append(indata.copy())
        # Calculate RMS volume level (0.0 to 1.0) and report to HUD
        rms = np.sqrt(np.mean(indata**2))
        vol = min(1.0, float(rms * 12.0))
        state.hud.set_volume(vol)

def start_recording():
    if state.recording:
        return
    state.audio_buffer = []
    state.recording = True
    state.set_status(Status.LISTENING)
    log(">>> RECORDING STARTED")
    if state.config.get("sound_effects", True):
        sound_effects.play_start_sound()

def stop_recording():
    if not state.recording:
        return None
    state.recording = False
    state.set_status(Status.TRANSCRIBING)
    log("<<< RECORDING STOPPED, processing...")
    if state.config.get("sound_effects", True):
        sound_effects.play_stop_sound()

    if not state.audio_buffer or len(state.audio_buffer) == 0:
        log("No audio captured")
        state.set_status(Status.IDLE)
        return None

    try:
        audio_data = np.concatenate(state.audio_buffer, axis=0)
    except Exception as e:
        log_error(f"Failed to concatenate audio: {e}")
        state.audio_buffer = []
        state.set_status(Status.IDLE)
        return None

    state.audio_buffer = []
    audio_len_sec = len(audio_data) / SAMPLE_RATE
    log(f"Captured {len(audio_data)} samples ({audio_len_sec:.1f}s)")
    return audio_data

def load_whisper_model(model_size=None):
    if model_size is None:
        model_size = state.config.get("model_size", "tiny")
    log(f"Loading Whisper '{model_size}' model with faster-whisper (int8 local)...")
    sys.stdout.flush()
    model = WhisperModel(model_size, device="auto", compute_type="int8", download_root=str(MODELS_DIR))
    log("Model loaded!")
    return model

def transcribe_audio(audio_data, model_override=None):
    if not state.model:
        return ""
    try:
        audio_1d = audio_data.squeeze()
        if len(audio_1d) < 4000 or np.max(np.abs(audio_1d)) < 0.001:
            log(f"Audio too quiet or too short ({len(audio_1d)} samples), skipping transcription")
            return ""
        
        lang = state.config.get("language", "en")
        if lang == "auto":
            lang = None

        custom_vocab = state.config.get("custom_vocabulary", "")
        prompt = custom_vocab if custom_vocab else None

        active_model = state.model
        if model_override and model_override != state.config.get("model_size"):
            # Load override model temporarily if needed
            active_model = load_whisper_model(model_override)

        segments, info = active_model.transcribe(audio_1d, language=lang, beam_size=5, initial_prompt=prompt)
        text = " ".join(segment.text for segment in segments).strip()
        log(f"Raw Transcription: \"{text}\"")
        return text
    except Exception as e:
        log_error(f"Transcription failed: {e}")
        return ""

# ==============================================================================
# CLIPBOARD & TEXT PASTE
# ==============================================================================

def set_clipboard_text(text):
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            return True
        except:
            time.sleep(0.05)
    return False

def get_clipboard_text():
    try:
        win32clipboard.OpenClipboard()
        try:
            text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        except:
            text = ""
        win32clipboard.CloseClipboard()
        return text
    except:
        return ""

def paste_at_cursor(text):
    if not text:
        log("Nothing to paste - text was empty")
        return False

    log(f"Pasting: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")

    saved = get_clipboard_text()
    if not set_clipboard_text(text):
        log_error("Could not set clipboard text")
        return False

    time.sleep(0.01)

    for attempt in range(3):
        try:
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 2, 0)
            ctypes.windll.user32.keybd_event(VK_SHIFT, 0, 2, 0)
            time.sleep(0.005)

            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            time.sleep(0.005)
            ctypes.windll.user32.keybd_event(0x56, 0, 0, 0)
            time.sleep(0.005)
            ctypes.windll.user32.keybd_event(0x56, 0, 2, 0)
            time.sleep(0.005)
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 2, 0)
            time.sleep(0.02)

            if saved:
                set_clipboard_text(saved)
            else:
                set_clipboard_text("")

            log("Paste successful!")
            state.transcribed_count += 1
            return True

        except Exception as e:
            log_error(f"Paste attempt {attempt+1} failed: {e}")
            time.sleep(0.2)

    return False

# ==============================================================================
# DICTATION WORKFLOW
# ==============================================================================

def toggle_dictation():
    now = time.time()
    if now - state.last_toggle < 1.0:
        return
    state.last_toggle = now
    try:
        if not state.recording:
            state.recording_started_at = now
            start_recording()
        else:
            elapsed = now - state.recording_started_at
            audio_data = stop_recording()
            if audio_data is None:
                return
            if elapsed < 0.8:
                log(f"Recording too short ({elapsed:.1f}s) - cancelled")
                state.set_status(Status.IDLE)
                return

            audio_clean = state.vad.extract_speech(audio_data)
            clean_len = len(audio_clean)

            if clean_len < 4000:
                log("Speech too quiet or no speech detected")
                state.set_status(Status.IDLE)
                return

            # Auto-switch mode based on focused window if enabled
            if state.config.get("auto_switch_modes", True):
                auto_mode = get_recommended_mode()
                if auto_mode != state.config.get("dictation_mode"):
                    log(f"Auto-switching dictation mode to '{auto_mode}' based on active window context")
                    state.config.set("dictation_mode", auto_mode)

            # Dynamic Routing: use 'tiny' fast path for short audio (< 3.0s) if enabled
            target_model = state.config.get("model_size", "tiny")
            if state.config.get("dynamic_routing", True) and elapsed < 3.0:
                log(f"Dynamic Routing: Using fast path model ('tiny') for {elapsed:.1f}s utterance")
                target_model = "tiny"

            raw_text = transcribe_audio(audio_clean, model_override=target_model)
            if raw_text:
                if state.config.get("sound_effects", True):
                    sound_effects.play_success_sound()
                # 1. Process Voice Commands & Punctuation & Macros
                processed_text, is_action = state.voice_cmd.process(raw_text)

                if is_action:
                    log(f"Executed System Voice Action: {processed_text}")
                    state.hud.show_toast(processed_text)
                else:
                    # 2. Clean Text (Filler Removal, Capitalization, Optional Local Ollama)
                    final_text = state.cleaner.clean(processed_text)
                    
                    # 3. Paste Text at Cursor
                    paste_at_cursor(final_text)

                    # 4. Show HUD toast preview
                    state.hud.show_toast(final_text)

                    # 5. Save to History
                    state.history.add_entry(raw_text, final_text, elapsed)
            else:
                log("No text returned from transcription")

            state.set_status(Status.IDLE)
    except Exception as e:
        log_error(f"toggle_dictation error: {e}")
        state.set_status(Status.IDLE)

# ==============================================================================
# SYSTEM TRAY MENU
# ==============================================================================

def create_icon(status):
    size = 64
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    if status == Status.LISTENING:
        color = (220, 40, 40)
    elif status == Status.TRANSCRIBING:
        color = (240, 160, 30)
    else:
        color = (40, 180, 40)
    draw.ellipse((2, 2, size-2, size-2), fill=color)
    draw.text((size//2-10, size//2-6), {
        Status.LISTENING: "REC",
        Status.TRANSCRIBING: "...",
        Status.IDLE: "OK"
    }.get(status, "?"), fill='white')
    return img

def create_menu():
    active_model = state.config.get("model_size", "tiny")
    active_profile = state.config.get("active_profile", "General")
    
    profile_menu = pystray.Menu(
        pystray.MenuItem("General Dictation", lambda: set_profile("General"), checked=lambda item: active_profile == "General"),
        pystray.MenuItem("Coding Mode", lambda: set_profile("Coding"), checked=lambda item: active_profile == "Coding"),
        pystray.MenuItem("Email & Messages", lambda: set_profile("Email"), checked=lambda item: active_profile == "Email"),
        pystray.MenuItem("Meeting Notes", lambda: set_profile("Meeting Notes"), checked=lambda item: active_profile == "Meeting Notes"),
    )

    items = [
        pystray.MenuItem(f"{APP_NAME} v{APP_VERSION}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🎛️ Control Panel & History", open_control_panel),
        pystray.MenuItem("👤 Preset Profiles", profile_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Status: {state.status.title()}", None, enabled=False),
        pystray.MenuItem(f"Transcriptions: {len(state.history.entries)}", None, enabled=False),
        pystray.MenuItem("Hotkey: Ctrl+Shift+Space", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Model: tiny", lambda icon, item: set_model("tiny"), checked=lambda item: active_model == "tiny"),
        pystray.MenuItem("Model: base", lambda icon, item: set_model("base"), checked=lambda item: active_model == "base"),
        pystray.MenuItem("Model: small", lambda icon, item: set_model("small"), checked=lambda item: active_model == "small"),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit),
    ]
    return pystray.Menu(*items)

def set_profile(profile_name):
    state.config.set("active_profile", profile_name)
    if profile_name == "Coding":
        state.config.set("dictation_mode", "coding")
    elif profile_name == "Meeting Notes":
        state.config.set("dictation_mode", "markdown")
    else:
        state.config.set("dictation_mode", "general")
    log(f"Switched profile to: {profile_name}")

def open_control_panel(icon=None, item=None):
    threading.Thread(target=state.gui.show, daemon=True).start()

def set_model(model_name):
    threading.Thread(target=state.reload_whisper_model, args=(model_name,), daemon=True).start()

def on_exit(icon, item):
    log("Shutting down...")
    state.recording = False
    stop_hotkey()
    if icon:
        icon.stop()
    os._exit(0)

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    log(f"{'='*50}")
    log(f"  {APP_NAME} v{APP_VERSION} (100% Local & Free)")
    log(f"{'='*50}")
    log("  Hotkey: Ctrl+Shift+Space")
    log(f"  Model:  {state.config.get('model_size', 'tiny')} (faster-whisper int8)")
    log(f"  Log:    {BASE_DIR / 'wispar_flow.log'}")
    log(f"{'='*50}")

    # Load Whisper model
    try:
        state.model = load_whisper_model()
        log("Warming up model...")
        dummy = np.zeros(SAMPLE_RATE, dtype=np.float32)
        segments, _ = state.model.transcribe(dummy, language="en")
        list(segments)
        log("Model ready!")
    except Exception as e:
        log_error(f"Failed to load model: {e}")
        return

    # Start system tray
    state.tray_icon = pystray.Icon("wispar_flow", create_icon(Status.IDLE),
                                    f"{APP_NAME} - Press Ctrl+Shift+Space", create_menu())
    tray_thread = threading.Thread(target=state.tray_icon.run, daemon=True)
    tray_thread.start()

    # Start hotkey hook
    hook_thread = threading.Thread(target=hotkey_thread_func, daemon=True)
    hook_thread.start()

    log("READY! Press Ctrl+Shift+Space to dictate anywhere.")
    log("Minimized to system tray (look for green circle).")
    log("=" * 50)

    # Start audio stream
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                           dtype=DTYPE, blocksize=BLOCK_SIZE,
                           callback=audio_callback):
            while True:
                time.sleep(1)
    except Exception as e:
        log_error(f"Audio stream error: {e}")
        time.sleep(5)

if __name__ == "__main__":
    main()
