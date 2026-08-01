"""
WISPAR FLOW - Floating Visual HUD Overlay
Semi-transparent top-most desktop widget showing real-time audio levels and status.
"""

import tkinter as tk
import threading
import time
import math

THEMES = {
    "Catppuccin": {
        "bg": "#1e1e2e", "border": "#313244", "text": "#cdd6f4",
        "dot_idle": "#a6e3a1", "dot_rec": "#f38ba8", "dot_trans": "#fab387", "bar": "#89b4fa"
    },
    "Nord": {
        "bg": "#2e3440", "border": "#4c566a", "text": "#eceff4",
        "dot_idle": "#a3be8c", "dot_rec": "#bf616a", "dot_trans": "#d08770", "bar": "#88c0d0"
    },
    "Cyberpunk": {
        "bg": "#0f0f1b", "border": "#ff007f", "text": "#00f0ff",
        "dot_idle": "#00ff66", "dot_rec": "#ff0055", "dot_trans": "#ffaa00", "bar": "#ff007f"
    },
    "OLED Dark": {
        "bg": "#000000", "border": "#222222", "text": "#ffffff",
        "dot_idle": "#00e676", "dot_rec": "#ff1744", "dot_trans": "#ff9100", "bar": "#29b6f6"
    }
}

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
        self.live_preview = ""
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._start_thread()

    def _get_theme(self):
        theme_name = self.config.get("hud_theme", "Catppuccin") if self.config else "Catppuccin"
        return THEMES.get(theme_name, THEMES["Catppuccin"])

    def _start_thread(self):
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()

    def _run_gui(self):
        try:
            theme = self._get_theme()
            self.root = tk.Tk()
            self.root.title("WISPAR FLOW HUD")
            self.root.overrideredirect(True)
            self.root.wm_attributes("-topmost", True)
            self.root.wm_attributes("-alpha", 0.94)
            self.root.configure(bg=theme["bg"])

            # Mouse Drag Bindings for Window Repositioning
            self.root.bind("<ButtonPress-1>", self._on_drag_start)
            self.root.bind("<B1-Motion>", self._on_drag_motion)

            # Center-bottom position default
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            w, h = 340, 56
            x = (screen_w - w) // 2
            y = screen_h - h - 80
            self.root.geometry(f"{w}x{h}+{x}+{y}")

            self.canvas = tk.Canvas(self.root, width=w, height=h, bg=theme["bg"], highlightthickness=0)
            self.canvas.pack(fill="both", expand=True)

            self.rect_bg = self.canvas.create_rectangle(4, 4, w-4, h-4, fill=theme["bg"], outline=theme["border"], width=2)
            self.dot = self.canvas.create_oval(14, 20, 30, 36, fill=theme["dot_idle"], outline="")
            self.text_id = self.canvas.create_text(38, 28, text="WISPAR FLOW - Ready", fill=theme["text"], font=("Segoe UI", 9, "bold"), anchor="w")

            self.wave_bars = []
            start_x = 265
            for i in range(5):
                bx = start_x + i * 11
                bar = self.canvas.create_rectangle(bx, 35, bx + 7, 37, fill=theme["bar"], outline="")
                self.wave_bars.append(bar)

            self.root.withdraw()
            self.is_running = True

            self._update_loop()
            self.root.mainloop()
        except Exception as e:
            print(f"[HUD Error] {e}")

    def _on_drag_start(self, event):
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_motion(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_start_x)
        y = self.root.winfo_y() + (event.y - self._drag_start_y)
        self.root.geometry(f"+{x}+{y}")

    def update_theme(self):
        if not self.root: return
        theme = self._get_theme()
        def _apply():
            self.root.configure(bg=theme["bg"])
            self.canvas.configure(bg=theme["bg"])
            self.canvas.itemconfig(self.rect_bg, fill=theme["bg"], outline=theme["border"])
            self.canvas.itemconfig(self.text_id, fill=theme["text"])
        self.root.after(0, _apply)

    def _update_loop(self):
        if not self.root:
            return
        try:
            theme = self._get_theme()
            self.anim_phase += 0.2
            start_x = 265
            max_h = 24
            base_y = 40

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

            if self.current_status == "listening":
                self.canvas.itemconfig(self.dot, fill=theme["dot_rec"])
                txt = f"Listening: \"{self.live_preview}\"" if self.live_preview else "Listening..."
                if len(txt) > 28: txt = txt[:25] + "..."
                self.canvas.itemconfig(self.text_id, text=txt)
                for bar in self.wave_bars: self.canvas.itemconfig(bar, fill=theme["dot_rec"])
            elif self.current_status == "transcribing":
                self.canvas.itemconfig(self.dot, fill=theme["dot_trans"])
                self.canvas.itemconfig(self.text_id, text="Transcribing...")
                for bar in self.wave_bars: self.canvas.itemconfig(bar, fill=theme["dot_trans"])
            elif not getattr(self, "_toast_active", False):
                self.canvas.itemconfig(self.dot, fill=theme["dot_idle"])
                self.canvas.itemconfig(self.text_id, text="WISPAR FLOW - Ready")
                for bar in self.wave_bars: self.canvas.itemconfig(bar, fill=theme["dot_idle"])

        except Exception:
            pass

        if self.root:
            self.root.after(40, self._update_loop)

    def set_live_preview(self, text: str):
        self.live_preview = text

    def set_status(self, status: str):
        self.current_status = status
        if not self.root: return

        if self.config and not self.config.get("hud_enabled", True):
            self.root.after(0, self.root.withdraw)
            return

        if status in ["listening", "transcribing"]:
            self._toast_active = False
            if status == "listening":
                self.live_preview = ""
            self.root.after(0, self.root.deiconify)
        else:
            def delayed_hide():
                time.sleep(1.8)
                if self.current_status == "idle" and self.root and not getattr(self, "_toast_active", False):
                    self.root.after(0, self.root.withdraw)
            threading.Thread(target=delayed_hide, daemon=True).start()

    def set_volume(self, level: float):
        self.volume_level = level

    def show_toast(self, text: str):
        if not self.root or not text: return
        if self.config and not self.config.get("hud_enabled", True): return

        self._toast_active = True
        snippet = text[:28] + "..." if len(text) > 28 else text
        def _update():
            theme = self._get_theme()
            self.root.deiconify()
            self.canvas.itemconfig(self.dot, fill=theme["bar"])
            self.canvas.itemconfig(self.text_id, text=f"Pasted: \"{snippet}\"")
        self.root.after(0, _update)

        def _clear_toast():
            time.sleep(2.0)
            self._toast_active = False
            if self.current_status == "idle" and self.root:
                self.root.after(0, self.root.withdraw)
        threading.Thread(target=_clear_toast, daemon=True).start()
