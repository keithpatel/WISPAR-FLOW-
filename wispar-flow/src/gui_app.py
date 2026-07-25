"""
WISPAR FLOW - Control Panel & History GUI App
Modern desktop application window built with tkinter & ttk.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox
import win32clipboard
import sounddevice as sd

class ControlPanelGUI:
    def __init__(self, config_manager, history_manager, on_model_change_cb=None):
        self.config = config_manager
        self.history = history_manager
        self.on_model_change_cb = on_model_change_cb
        self.root = None

    def show(self):
        """Open or bring to front the Control Panel window."""
        if self.root is not None and self.root.winfo_exists():
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            return

        self.root = tk.Tk()
        self.root.title("WISPAR FLOW - Control Panel")
        self.root.geometry("700x520")
        self.root.minsize(640, 450)
        self.root.configure(bg="#1e1e2e")

        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4", padding=[12, 6], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", "#89b4fa")], foreground=[("selected", "#11111b")])
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("TButton", background="#89b4fa", foreground="#11111b", font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", "#b4befe")])

        # Header Title Banner
        header = tk.Frame(self.root, bg="#181825", height=50)
        header.pack(fill="x", side="top")
        lbl_title = tk.Label(header, text="🎙️ WISPAR FLOW Control Panel", font=("Segoe UI", 14, "bold"), bg="#181825", fg="#89b4fa")
        lbl_title.pack(side="left", padx=15, pady=10)

        lbl_ver = tk.Label(header, text="v2.0 (100% Local & Offline)", font=("Segoe UI", 9), bg="#181825", fg="#a6adc8")
        lbl_ver.pack(side="right", padx=15, pady=10)

        # Tabbed Layout
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_dash = ttk.Frame(notebook)
        tab_hist = ttk.Frame(notebook)
        tab_macros = ttk.Frame(notebook)
        tab_settings = ttk.Frame(notebook)

        notebook.add(tab_dash, text=" 📊 Dashboard ")
        notebook.add(tab_hist, text=" 📜 History ")
        notebook.add(tab_macros, text=" 💬 Voice Macros ")
        notebook.add(tab_settings, text=" ⚙️ Settings ")

        self._build_dashboard(tab_dash)
        self._build_history(tab_hist)
        self._build_macros(tab_macros)
        self._build_settings(tab_settings)

        self.root.mainloop()

    def _build_dashboard(self, parent):
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Cards Frame
        cards_frame = tk.Frame(frame, bg="#1e1e2e")
        cards_frame.pack(fill="x", pady=8)

        # Card 1: Transcriptions Count
        card1 = tk.Frame(cards_frame, bg="#313244", padx=12, pady=12, highlightthickness=1, highlightbackground="#45475a")
        card1.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(card1, text="Total Transcriptions", font=("Segoe UI", 9), bg="#313244", fg="#a6adc8").pack(anchor="w")
        self.lbl_hist_count = tk.Label(card1, text=str(len(self.history.entries)), font=("Segoe UI", 18, "bold"), bg="#313244", fg="#a6e3a1")
        self.lbl_hist_count.pack(anchor="w", pady=(2, 0))

        # Card 2: Total Words
        card2 = tk.Frame(cards_frame, bg="#313244", padx=12, pady=12, highlightthickness=1, highlightbackground="#45475a")
        card2.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(card2, text="Total Words Spoken", font=("Segoe UI", 9), bg="#313244", fg="#a6adc8").pack(anchor="w")
        self.lbl_words_val = tk.Label(card2, text=str(self.history.get_total_words()), font=("Segoe UI", 18, "bold"), bg="#313244", fg="#f9e2af")
        self.lbl_words_val.pack(anchor="w", pady=(2, 0))

        # Card 3: Time Saved
        card3 = tk.Frame(cards_frame, bg="#313244", padx=12, pady=12, highlightthickness=1, highlightbackground="#45475a")
        card3.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(card3, text="Typing Time Saved", font=("Segoe UI", 9), bg="#313244", fg="#a6adc8").pack(anchor="w")
        self.lbl_saved_val = tk.Label(card3, text=f"{self.history.get_time_saved_minutes()}m", font=("Segoe UI", 18, "bold"), bg="#313244", fg="#cba6f7")
        self.lbl_saved_val.pack(anchor="w", pady=(2, 0))

        # Card 4: Current Model
        card4 = tk.Frame(cards_frame, bg="#313244", padx=12, pady=12, highlightthickness=1, highlightbackground="#45475a")
        card4.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(card4, text="Active Model", font=("Segoe UI", 9), bg="#313244", fg="#a6adc8").pack(anchor="w")
        self.lbl_model_val = tk.Label(card4, text=self.config.get("model_size", "tiny").upper(), font=("Segoe UI", 18, "bold"), bg="#313244", fg="#89b4fa")
        self.lbl_model_val.pack(anchor="w", pady=(2, 0))

        # Mode Selection & Toggles Section
        toggles_frame = tk.LabelFrame(frame, text=" Configuration & Toggles ", font=("Segoe UI", 10, "bold"), bg="#1e1e2e", fg="#cdd6f4", padx=15, pady=10)
        toggles_frame.pack(fill="x", pady=10)

        f_mode = tk.Frame(toggles_frame, bg="#1e1e2e")
        f_mode.pack(fill="x", pady=4)
        tk.Label(f_mode, text="Dictation Mode:", font=("Segoe UI", 10, "bold"), bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.cb_mode = ttk.Combobox(f_mode, values=["general", "coding", "markdown"], state="readonly", width=16)
        self.cb_mode.set(self.config.get("dictation_mode", "general"))
        self.cb_mode.pack(side="left", padx=8)
        self.cb_mode.bind("<<ComboboxSelected>>", self._on_mode_selected)

        self.var_hud = tk.BooleanVar(value=self.config.get("hud_enabled", True))
        cb_hud = tk.Checkbutton(toggles_frame, text="Show Floating Audio HUD Overlay & Waveform", variable=self.var_hud, command=self._save_toggles, bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e", activeforeground="#cdd6f4", font=("Segoe UI", 10))
        cb_hud.pack(anchor="w", pady=4)

        self.var_fillers = tk.BooleanVar(value=self.config.get("remove_fillers", True))
        cb_fillers = tk.Checkbutton(toggles_frame, text="Remove Filler Words ('um', 'uh', 'like')", variable=self.var_fillers, command=self._save_toggles, bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e", activeforeground="#cdd6f4", font=("Segoe UI", 10))
        cb_fillers.pack(anchor="w", pady=4)

        self.var_punc = tk.BooleanVar(value=self.config.get("auto_punctuation", True))
        cb_punc = tk.Checkbutton(toggles_frame, text="Enable Voice Punctuation ('period', 'new line')", variable=self.var_punc, command=self._save_toggles, bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e", activeforeground="#cdd6f4", font=("Segoe UI", 10))
        cb_punc.pack(anchor="w", pady=4)

    def _on_mode_selected(self, event=None):
        self.config.set("dictation_mode", self.cb_mode.get())

    def _save_toggles(self):
        self.config.set("hud_enabled", self.var_hud.get())
        self.config.set("remove_fillers", self.var_fillers.get())
        self.config.set("auto_punctuation", self.var_punc.get())

    def _build_history(self, parent):
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Search Bar & Action Buttons Bar
        top_bar = tk.Frame(frame, bg="#1e1e2e")
        top_bar.pack(fill="x", pady=(0, 8))

        tk.Label(top_bar, text="🔍 Search:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.ent_search = ttk.Entry(top_bar, width=22)
        self.ent_search.pack(side="left", padx=5)
        self.ent_search.bind("<KeyRelease>", self._on_search_history)

        btn_copy = ttk.Button(top_bar, text="📋 Copy Text", command=self._copy_selected_hist)
        btn_copy.pack(side="left", padx=4)

        btn_del = ttk.Button(top_bar, text="🗑️ Delete", command=self._delete_selected_hist)
        btn_del.pack(side="left", padx=4)

        # Export Dropdown
        btn_exp_csv = ttk.Button(top_bar, text="💾 Export CSV", command=lambda: self._export_history("csv"))
        btn_exp_csv.pack(side="right", padx=2)

        btn_exp_txt = ttk.Button(top_bar, text="💾 Export TXT", command=lambda: self._export_history("txt"))
        btn_exp_txt.pack(side="right", padx=2)

        btn_exp_md = ttk.Button(top_bar, text="💾 Export MD", command=lambda: self._export_history("md"))
        btn_exp_md.pack(side="right", padx=2)

        # Treeview Table
        columns = ("id", "timestamp", "duration", "text")
        self.tree_hist = ttk.Treeview(frame, columns=columns, show="headings", height=12)
        self.tree_hist.heading("timestamp", text="Time")
        self.tree_hist.heading("duration", text="Duration")
        self.tree_hist.heading("text", text="Transcribed Text")
        self.tree_hist.column("id", width=0, stretch=False)
        self.tree_hist.column("timestamp", width=140)
        self.tree_hist.column("duration", width=70)
        self.tree_hist.column("text", width=420)
        self.tree_hist.pack(fill="both", expand=True)

        self._refresh_history_table()

    def _on_search_history(self, event=None):
        query = self.ent_search.get().strip()
        results = self.history.search_entries(query)
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)
        for entry in results:
            self.tree_hist.insert("", "end", values=(entry.get("id"), entry.get("timestamp"), f"{entry.get('duration', 0)}s", entry.get("final_text")))

    def _refresh_history_table(self):
        for item in self.tree_hist.get_children():
            self.tree_hist.delete(item)
        for entry in self.history.get_history(100):
            self.tree_hist.insert("", "end", values=(entry.get("id"), entry.get("timestamp"), f"{entry.get('duration', 0)}s", entry.get("final_text")))
        if hasattr(self, 'lbl_hist_count') and self.lbl_hist_count:
            self.lbl_hist_count.config(text=str(len(self.history.entries)))
        if hasattr(self, 'lbl_words_val') and self.lbl_words_val:
            self.lbl_words_val.config(text=str(self.history.get_total_words()))
        if hasattr(self, 'lbl_saved_val') and self.lbl_saved_val:
            self.lbl_saved_val.config(text=f"{self.history.get_time_saved_minutes()}m")

    def _export_history(self, fmt: str):
        from tkinter import filedialog
        filetypes = {
            "csv": [("CSV Files", "*.csv")],
            "txt": [("Text Files", "*.txt")],
            "md": [("Markdown Files", "*.md")]
        }
        path = filedialog.asksaveasfilename(
            title=f"Export History as .{fmt}",
            defaultextension=f".{fmt}",
            filetypes=filetypes.get(fmt, [("All Files", "*.*")])
        )
        if not path:
            return
        try:
            if fmt == "csv":
                self.history.export_csv(path)
            elif fmt == "txt":
                self.history.export_txt(path)
            elif fmt == "md":
                self.history.export_markdown(path)
            messagebox.showinfo("Export Success", f"History successfully exported to {path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export history: {e}")

    def _copy_selected_hist(self):
        sel = self.tree_hist.selection()
        if not sel:
            messagebox.showinfo("History", "Please select a transcription row first.")
            return
        vals = self.tree_hist.item(sel[0], "values")
        text = vals[3]
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        messagebox.showinfo("History", "Text copied to clipboard!")

    def _delete_selected_hist(self):
        sel = self.tree_hist.selection()
        if not sel:
            return
        vals = self.tree_hist.item(sel[0], "values")
        entry_id = int(vals[0])
        self.history.delete_entry(entry_id)
        self._refresh_history_table()

    def _clear_all_hist(self):
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all history logs?"):
            self.history.clear()
            self._refresh_history_table()

    def _build_macros(self, parent):
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        lbl = tk.Label(frame, text="Custom Voice Replacements & Dynamic Placeholders ({date}, {time}, {clipboard})", bg="#1e1e2e", fg="#a6adc8")
        lbl.pack(anchor="w", pady=5)

        # Form to add new macro
        form = tk.Frame(frame, bg="#1e1e2e")
        form.pack(fill="x", pady=5)

        tk.Label(form, text="Spoken Phrase:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.ent_phrase = ttk.Entry(form, width=18)
        self.ent_phrase.pack(side="left", padx=5)

        tk.Label(form, text="Replaces With:", bg="#1e1e2e", fg="#cdd6f4").pack(side="left", padx=(8, 0))
        self.ent_replacement = ttk.Entry(form, width=24)
        self.ent_replacement.pack(side="left", padx=5)

        btn_add = ttk.Button(form, text="➕ Add Macro", command=self._add_macro)
        btn_add.pack(side="left", padx=5)

        # Macro list table
        self.tree_macros = ttk.Treeview(frame, columns=("phrase", "replacement"), show="headings", height=8)
        self.tree_macros.heading("phrase", text="Spoken Voice Phrase")
        self.tree_macros.heading("replacement", text="Pasted Text Output")
        self.tree_macros.column("phrase", width=230)
        self.tree_macros.column("replacement", width=400)
        self.tree_macros.pack(fill="both", expand=True, pady=10)

        btn_del_macro = ttk.Button(frame, text="🗑️ Remove Selected Macro", command=self._del_macro)
        btn_del_macro.pack(anchor="e")

        self._refresh_macros_table()

    def _refresh_macros_table(self):
        for item in self.tree_macros.get_children():
            self.tree_macros.delete(item)
        custom = self.config.get("custom_replacements", {})
        for k, v in custom.items():
            self.tree_macros.insert("", "end", values=(k, v))

    def _add_macro(self):
        phrase = self.ent_phrase.get().strip().lower()
        repl = self.ent_replacement.get().strip()
        if not phrase or not repl:
            messagebox.showwarning("Voice Macros", "Both Spoken Phrase and Replacement fields are required.")
            return
        custom = self.config.get("custom_replacements", {})
        custom[phrase] = repl
        self.config.set("custom_replacements", custom)
        self.ent_phrase.delete(0, "end")
        self.ent_replacement.delete(0, "end")
        self._refresh_macros_table()

    def _del_macro(self):
        sel = self.tree_macros.selection()
        if not sel:
            return
        vals = self.tree_macros.item(sel[0], "values")
        phrase = vals[0]
        custom = self.config.get("custom_replacements", {})
        if phrase in custom:
            del custom[phrase]
            self.config.set("custom_replacements", custom)
        self._refresh_macros_table()

    def _build_settings(self, parent):
        frame = tk.Frame(parent, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        # 1. Model Selector
        f1 = tk.Frame(frame, bg="#1e1e2e")
        f1.pack(fill="x", pady=6)
        tk.Label(f1, text="Whisper Model Size:", font=("Segoe UI", 10, "bold"), width=20, anchor="w", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.cb_model = ttk.Combobox(f1, values=["tiny", "base", "small"], state="readonly", width=15)
        self.cb_model.set(self.config.get("model_size", "tiny"))
        self.cb_model.pack(side="left", padx=5)

        # 2. Language Selector
        f2 = tk.Frame(frame, bg="#1e1e2e")
        f2.pack(fill="x", pady=6)
        tk.Label(f2, text="Transcribe Language:", font=("Segoe UI", 10, "bold"), width=20, anchor="w", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.cb_lang = ttk.Combobox(f2, values=["en", "auto", "es", "fr", "de", "zh", "ja", "it"], state="readonly", width=15)
        self.cb_lang.set(self.config.get("language", "en"))
        self.cb_lang.pack(side="left", padx=5)

        # 3. Custom Vocabulary (Initial Prompt)
        f3 = tk.Frame(frame, bg="#1e1e2e")
        f3.pack(fill="x", pady=6)
        tk.Label(f3, text="Custom Vocabulary:", font=("Segoe UI", 10, "bold"), width=20, anchor="w", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        self.ent_vocab = ttk.Entry(f3, width=42)
        self.ent_vocab.insert(0, self.config.get("custom_vocabulary", ""))
        self.ent_vocab.pack(side="left", padx=5)

        # 4. Audio Input Device Selector
        f4 = tk.Frame(frame, bg="#1e1e2e")
        f4.pack(fill="x", pady=6)
        tk.Label(f4, text="Microphone Input:", font=("Segoe UI", 10, "bold"), width=20, anchor="w", bg="#1e1e2e", fg="#cdd6f4").pack(side="left")
        
        devices = []
        try:
            devs = sd.query_devices()
            devices = [f"{i}: {d['name']}" for i, d in enumerate(devs) if d['max_input_channels'] > 0]
        except:
            devices = ["Default Microphone"]
            
        self.cb_dev = ttk.Combobox(f4, values=["Default Microphone"] + devices, state="readonly", width=40)
        self.cb_dev.set("Default Microphone")
        self.cb_dev.pack(side="left", padx=5)

        # Save Settings Button
        btn_save = ttk.Button(frame, text="💾 Save & Apply Settings", command=self._save_settings)
        btn_save.pack(anchor="w", pady=20)

    def _save_settings(self):
        new_model = self.cb_model.get()
        new_lang = self.cb_lang.get()
        new_vocab = self.ent_vocab.get().strip()
        old_model = self.config.get("model_size")

        self.config.set("model_size", new_model)
        self.config.set("language", new_lang)
        self.config.set("custom_vocabulary", new_vocab)

        if hasattr(self, 'lbl_model_val') and self.lbl_model_val:
            self.lbl_model_val.config(text=new_model.upper())

        if new_model != old_model and self.on_model_change_cb:
            messagebox.showinfo("Settings", f"Whisper model changed to '{new_model}'. Reloading model...")
            self.on_model_change_cb(new_model)
        else:
            messagebox.showinfo("Settings", "Settings saved successfully!")
