"""
WISPAR FLOW - Transcription History Logger
Stores transcription logs locally in wispar_history.json
"""

import json
import time
import datetime
from pathlib import Path

class HistoryManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        else:
            base_dir = Path(base_dir)
        self.file_path = base_dir / "wispar_history.json"
        self.entries = []
        self.load()

    def load(self):
        """Load history from disk."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception as e:
                print(f"[History] Error loading history: {e}")
                self.entries = []
        else:
            self.entries = []

    def save(self):
        """Save history to disk."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, indent=2)
        except Exception as e:
            print(f"[History] Error saving history: {e}")

    def add_entry(self, raw_text: str, final_text: str, duration: float = 0.0):
        """Add a new transcription record to history."""
        if not final_text and not raw_text:
            return

        now = datetime.datetime.now()
        entry = {
            "id": int(time.time() * 1000),
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "raw_text": raw_text,
            "final_text": final_text,
            "duration": round(duration, 1),
            "char_count": len(final_text)
        }
        self.entries.insert(0, entry)  # newest first
        # Keep maximum 500 entries to maintain performance
        if len(self.entries) > 500:
            self.entries = self.entries[:500]
        self.save()

    def get_history(self, limit: int = 100):
        """Return history entries up to limit."""
        return self.entries[:limit]

    def clear(self):
        """Clear all history entries."""
        self.entries = []
        self.save()

    def delete_entry(self, entry_id: int):
        """Delete specific entry by ID."""
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        self.save()

    def search_entries(self, query: str):
        """Search history entries by query string."""
        if not query:
            return self.entries
        q = query.lower()
        return [
            e for e in self.entries
            if q in e.get("final_text", "").lower() or q in e.get("timestamp", "").lower()
        ]

    def get_total_words(self) -> int:
        """Calculate total words transcribed across history."""
        total = 0
        for e in self.entries:
            text = e.get("final_text", "")
            if text and not text.startswith("[Action:"):
                total += len(text.split())
        return total

    def get_time_saved_minutes(self) -> float:
        """Estimate typing time saved in minutes (assuming 40 WPM average typing speed)."""
        words = self.get_total_words()
        return round(words / 40.0, 1)

    def export_csv(self, file_path: str):
        """Export history entries to a CSV file."""
        import csv
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Timestamp", "Duration(s)", "Final Text", "Raw Text"])
            for e in self.entries:
                writer.writerow([
                    e.get("id"),
                    e.get("timestamp"),
                    e.get("duration"),
                    e.get("final_text"),
                    e.get("raw_text")
                ])

    def export_txt(self, file_path: str):
        """Export history entries to a TXT file."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"=== WISPAR FLOW Transcription History ===\n\n")
            for e in self.entries:
                f.write(f"[{e.get('timestamp')}] ({e.get('duration')}s):\n{e.get('final_text')}\n\n")

    def export_markdown(self, file_path: str):
        """Export history entries to a Markdown file."""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# 🎙️ WISPAR FLOW Transcription History\n\n")
            for e in self.entries:
                f.write(f"### {e.get('timestamp')} *({e.get('duration')}s)*\n")
                f.write(f"> {e.get('final_text')}\n\n")
