"""
WISPAR FLOW - Window Tracker
Detects the active focused window and maps it to dictation modes (coding, markdown, general).
"""

import win32gui
import win32process
import os

CODING_PROCESSES = ["code.exe", "devenv.exe", "pycharm64.exe", "idea64.exe", "sublime_text.exe", "atom.exe", "webstorm64.exe"]
MARKDOWN_PROCESSES = ["obsidian.exe", "typora.exe", "notion.exe"]

def get_active_window_info():
    """Returns (window_title, process_name)."""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return "", ""
        title = win32gui.GetWindowText(hwnd)
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        # Get process executable name using win32 API
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        h_process = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not h_process:
            return title, ""

        buf = ctypes.create_unicode_buffer(512)
        size = wintypes.DWORD(512)
        if ctypes.windll.psapi.GetModuleFileNameExW(h_process, 0, buf, size):
            process_name = os.path.basename(buf.value)
        else:
            process_name = ""

        ctypes.windll.kernel32.CloseHandle(h_process)
        return title, process_name
    except Exception:
        return "", ""

def get_recommended_mode():
    """Detects mode based on current active window."""
    title, proc = get_active_window_info()
    proc_lower = proc.lower()
    title_lower = title.lower()

    if proc_lower in CODING_PROCESSES or any(ext in title_lower for ext in [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".rs"]):
        return "coding"
    elif proc_lower in MARKDOWN_PROCESSES or ".md" in title_lower or "notes" in title_lower:
        return "markdown"
    return "general"
