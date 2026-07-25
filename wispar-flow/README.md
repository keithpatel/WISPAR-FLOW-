# WISPAR FLOW v2.0

Local offline voice dictation for Windows. Press **Ctrl+Shift+Space** to start/stop recording and paste transcribed text anywhere.

100% local & free — zero paid APIs.

## Features

- **Offline Speech-to-Text** — Powered by faster-whisper (OpenAI Whisper) running entirely on your machine
- **Global Hotkey** — Ctrl+Shift+Space toggles recording from any application
- **System Tray** — Minimal tray icon with status indicator (green/red/orange) and right-click menu to switch models, open control panel, or exit
- **Floating HUD Overlay** — Semi-transparent widget showing real-time audio waveform, status, and transcribed text preview
- **Control Panel GUI** — Desktop window with Dashboard stats, History log, Voice Macros editor, and Settings
- **Voice Commands** — Say "undo that", "copy that", "paste that", "new line", "period", "comma", "open notepad", and more
- **Text Cleaning** — Automatic filler word removal ("um", "uh", "like"), sentence capitalization, stutter correction
- **Dictation Modes** — General, Coding (snake_case, camelCase, PascalCase), and Markdown (headers, code blocks, task items)
- **Custom Voice Macros** — Define spoken phrase replacements with dynamic placeholders ({date}, {time}, {clipboard})
- **Transcription History** — Searchable log with export to CSV, TXT, or Markdown
- **Optional Ollama Integration** — Post-process text with a local LLM for grammar/spelling fixes
- **Voice Activity Detection** — Automatically trims silence from recordings
- **Multi-language** — Supports English, Spanish, French, German, Chinese, Japanese, Italian, plus auto-detect

## Requirements

- Windows (uses Win32 API for hotkeys, clipboard, and paste)
- Python 3.8+
- Microphone

## Quick Start

```batch
install_and_run.bat
```

Or manually:

```batch
pip install -r requirements.txt
python run.py
```

On first launch, WISPAR FLOW will download the Whisper AI model (~72MB for "tiny", ~140MB for "base").

## Usage

1. Launch the application — it minimizes to the system tray (green circle icon)
2. Press **Ctrl+Shift+Space** to start recording (HUD overlay appears)
3. Speak naturally into your microphone
4. Press **Ctrl+Shift+Space** again to stop — transcribed text is pasted at your cursor

Right-click the tray icon to:
- Open the Control Panel & History
- Switch between model sizes (tiny / base / small)
- Exit the application

## Project Structure

```
wispar-flow/
├── run.py                    # Application entry point
├── requirements.txt          # Python dependencies
├── wispar_config.json        # User configuration file
├── wispar_history.json       # Transcription history log
├── build_exe.bat             # PyInstaller build script
├── install_and_run.bat       # One-click install & launch
├── start_wispar.bat          # Launch (uses .venv)
├── debug_test.bat            # Self-test mode
├── src/
│   ├── dictate.py            # Core: audio capture, transcription, paste, system tray, hotkey
│   ├── config.py             # Configuration manager (JSON-backed settings)
│   ├── voice_commands.py     # Spoken command processing, macros, punctuation
│   ├── text_cleaner.py       # Filler removal, capitalization, coding/markdown transforms
│   ├── history_manager.py    # Transcription history with search and export
│   ├── hud_overlay.py        # Floating HUD overlay with waveform visualizer
│   └── gui_app.py            # Control panel desktop GUI (tkinter)
├── models/                   # Whisper model download directory
└── .gitignore
```

## Configuration

Settings are stored in `wispar_config.json`. Key options:

| Key | Default | Description |
|-----|---------|-------------|
| `model_size` | `"tiny"` | Whisper model: tiny, base, small |
| `language` | `"en"` | Language code or "auto" |
| `dictation_mode` | `"general"` | general, coding, or markdown |
| `hotkey` | `"Ctrl+Shift+Space"` | Global recording hotkey |
| `vad_threshold` | `0.008` | Voice activity sensitivity |
| `remove_fillers` | `true` | Remove "um"/"uh" filler words |
| `auto_punctuation` | `true` | Enable voice punctuation commands |
| `hud_enabled` | `true` | Show floating HUD overlay |
| `ollama_enabled` | `false` | Enable local Ollama post-processing |

## Building a Standalone EXE

```batch
build_exe.bat
```

Requires PyInstaller. Output: `dist/WISPAR_FLOW.exe`

## License

MIT
