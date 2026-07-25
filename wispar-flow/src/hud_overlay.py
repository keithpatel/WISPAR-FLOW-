"""
WISPAR FLOW - Floating Visual HUD Overlay
Semi-transparent top-most desktop widget showing real-time audio levels and status.
"""

import tkinter as tk
import threading
import time

import math

class HUDOverlay:
    def __init__(self, config_manager=None):
        self.config = config_manager
        self.root = None
        self.canvas = None
        self.status_label = None
        self.current_status = "idle"
        self.volume_level = 0.0  # 0.0 to 1.0
        self.is_running = False
        self.thread = None
        self.wave_bars = []
        self.anim_phase = 0.0
        self._start_thread()

    def _start_thread(self):
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()

    def _run_gui(self):
        try:
            self.root = tk.Tk()
            self.root.title("WISPAR FLOW HUD")
            self.root.overrideredirect(True)
            self.root.wm_attributes("-topmost", True)
            self.root.wm_attributes("-alpha", 0.92)
            self.root.configure(bg="#1e1e2e")

            # Center-bottom position
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            w, h = 300, 54
            x = (screen_w - w) // 2
            y = screen_h - h - 80
            self.root.geometry(f"{w}x{h}+{x}+{y}")

            # Canvas container for rounded aesthetic
            self.canvas = tk.Canvas(self.root, width=w, height=h, bg="#1e1e2e", highlightthickness=0)
            self.canvas.pack(fill="both", expand=True)

            # Background pill
            self.canvas.create_rectangle(4, 4, w-4, h-4, fill="#1e1e2e", outline="#313244", width=2)

            # Status dot
            self.dot = self.canvas.create_oval(14, 19, 30, 35, fill="#a6e3a1", outline="")

            # Text
            self.text_id = self.canvas.create_text(38, 27, text="WISPAR FLOW - Ready", fill="#cdd6f4", font=("Segoe UI", 9, "bold"), anchor="w")

            # Audio 5-Bar Equalizer Visualizer
            self.wave_bars = []
            start_x = 225
            for i in range(5):
                bx = start_x + i * 11
                bar = self.canvas.create_rectangle(bx, 34, bx + 7, 36, fill="#89b4fa", outline="")
                self.wave_bars.append(bar)

            # Start hidden by default
            self.root.withdraw()
            self.is_running = True

            # Periodic GUI update loop
            self._update_loop()
            self.root.mainloop()
        except Exception as e:
            print(f"[HUD Error] {e}")

    def _update_loop(self):
        if not self.root:
            return
        try:
            self.anim_phase += 0.2
            start_x = 225
            max_h = 24
            base_y = 39

            # Update 5 Waveform Bars
            for i, bar in enumerate(self.wave_bars):
                bx = start_x + i * 11
                if self.current_status == "listening":
                    wave_mult = math.sin(self.anim_phase + i * 0.8) * 0.3 + 0.7
                    height = int(max(4, self.volume_level * max_h * wave_mult))
                elif self.current_status == "transcribing":
                    height = int(max(4, (math.sin(self.anim_phase + i * 1.2) + 1.2) * 8))
                else:
                    height = 3

                self.canvas.coords(bar, bx, base_y - height, bx + 7, base_y)

            # Color coding for status
            if self.current_status == "listening":
                self.canvas.itemconfig(self.dot, fill="#f38ba8")  # Red
                self.canvas.itemconfig(self.text_id, text="Listening...")
                for bar in self.wave_bars:
                    self.canvas.itemconfig(bar, fill="#f38ba8")
            elif self.current_status == "transcribing":
                self.canvas.itemconfig(self.dot, fill="#fab387")  # Orange
                self.canvas.itemconfig(self.text_id, text="Transcribing...")
                for bar in self.wave_bars:
                    self.canvas.itemconfig(bar, fill="#fab387")
            elif not hasattr(self, "_toast_active") or not self._toast_active:
                self.canvas.itemconfig(self.dot, fill="#a6e3a1")  # Green
                self.canvas.itemconfig(self.text_id, text="WISPAR FLOW - Ready")
                for bar in self.wave_bars:
                    self.canvas.itemconfig(bar, fill="#a6e3a1")

        except Exception:
            pass

        if self.root:
            self.root.after(40, self._update_loop)

    def set_status(self, status: str):
        self.current_status = status
        if not self.root:
            return

        # Check config setting
        if self.config and not self.config.get("hud_enabled", True):
            self.root.after(0, self.root.withdraw)
            return

        if status in ["listening", "transcribing"]:
            self._toast_active = False
            self.root.after(0, self.root.deiconify)
        else:
            # Hide HUD after brief delay when returning to idle (unless toast active)
            def delayed_hide():
                time.sleep(1.8)
                if self.current_status == "idle" and self.root and not getattr(self, "_toast_active", False):
                    self.root.after(0, self.root.withdraw)
            threading.Thread(target=delayed_hide, daemon=True).start()

    def set_volume(self, level: float):
        """Update volume level (0.0 to 1.0)."""
        self.volume_level = level

    def show_toast(self, text: str):
        """Display brief floating preview of transcribed text."""
        if not self.root or not text:
            return
        if self.config and not self.config.get("hud_enabled", True):
            return

        self._toast_active = True
        snippet = text[:32] + "..." if len(text) > 32 else text
        def _update():
            self.root.deiconify()
            self.canvas.itemconfig(self.dot, fill="#89b4fa")
            self.canvas.itemconfig(self.text_id, text=f"Pasted: \"{snippet}\"")
        self.root.after(0, _update)

        def _clear_toast():
            time.sleep(2.0)
            self._toast_active = False
            if self.current_status == "idle" and self.root:
                self.root.after(0, self.root.withdraw)
        threading.Thread(target=_clear_toast, daemon=True).start()
