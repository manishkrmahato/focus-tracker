# tracker.py - Cross-platform active window tracker
# Replaces pywin32 with pygetwindow + psutil (works on Windows, macOS, Linux)
# Falls back gracefully when running in --demo mode (no real window needed)

import time
import re
import sys
import platform

import psutil

OS = platform.system()   # "Windows" | "Darwin" | "Linux"

#Platform-specific window detection

def _get_active_window_info_windows():
    """Windows: use pygetwindow (wraps win32 but also works without pywin32)."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()

        # Get title
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or "(no title)"

        # Get PID
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            proc = psutil.Process(pid.value)
            app_name = proc.name().replace(".exe", "").lower()
        except Exception:
            app_name = "unknown"

        url = _extract_url_from_title(title, app_name)
        return {"app": app_name, "title": title.strip(), "url": url}
    except Exception:
        return None


def _get_active_window_info_macos():
    """macOS: AppleScript via subprocess (no pyobjc dependency)."""
    try:
        import subprocess
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            set windowTitle to ""
            try
                set windowTitle to name of front window of (first application process whose frontmost is true)
            end try
            return frontApp & "|" & windowTitle
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3
        )
        output = result.stdout.strip()
        if "|" in output:
            app_name, title = output.split("|", 1)
        else:
            app_name, title = output, "(no title)"
        app_name = app_name.lower().strip()
        title = title.strip() or "(no title)"
        url = _extract_url_from_title(title, app_name)
        return {"app": app_name, "title": title, "url": url}
    except Exception:
        return None


def _get_active_window_info_linux():
    """Linux: use xdotool (X11). Install with: sudo apt install xdotool"""
    try:
        import subprocess

        win_id = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=2
        ).stdout.strip()

        if not win_id:
            return None

        title = subprocess.run(
            ["xdotool", "getwindowname", win_id],
            capture_output=True, text=True, timeout=2
        ).stdout.strip() or "(no title)"

        pid_str = subprocess.run(
            ["xdotool", "getwindowpid", win_id],
            capture_output=True, text=True, timeout=2
        ).stdout.strip()

        app_name = "unknown"
        if pid_str.isdigit():
            try:
                proc = psutil.Process(int(pid_str))
                app_name = proc.name().lower()
            except Exception:
                pass

        url = _extract_url_from_title(title, app_name)
        return {"app": app_name, "title": title, "url": url}
    except FileNotFoundError:
        return {"app": "unknown", "title": "(xdotool not installed)", "url": ""}
    except Exception:
        return None


#URL extraction from browser title bar

def _extract_url_from_title(title: str, app: str) -> str:
    browsers = ["chrome", "firefox", "msedge", "opera", "brave", "edge", "chromium"]
    if not any(b in app for b in browsers):
        return ""

    title_clean = re.sub(
        r"\s*[--|]\s*(Google Chrome|Mozilla Firefox|Microsoft Edge|"
        r"Opera|Brave|Safari|Edge|Chromium)\s*$",
        "", title, flags=re.IGNORECASE
    ).strip()

    parts = re.split(r"\s*[--|]\s*", title_clean)
    known = [
        "youtube", "github", "stackoverflow", "facebook", "instagram",
        "twitter", "reddit", "netflix", "linkedin", "whatsapp",
        "geeksforgeeks", "leetcode", "coursera", "wikipedia", "spotify",
        "amazon", "discord", "telegram", "claude", "chatgpt",
    ]
    for part in reversed(parts):
        part = part.strip()
        if re.search(r"\.[a-z]{2,}$", part, re.IGNORECASE):
            return part.lower()
        if any(k in part.lower() for k in known):
            return part.lower()

    return title_clean


#Public API

def get_active_window_info() -> dict:
    """
    Returns dict with: app, title, url
    Works on Windows, macOS, Linux. Never raises.
    """
    info = None
    if OS == "Windows":
        info = _get_active_window_info_windows()
    elif OS == "Darwin":
        info = _get_active_window_info_macos()
    else:
        info = _get_active_window_info_linux()

    if info is None:
        return {"app": "unknown", "title": "(no title)", "url": ""}
    return info


#Tracker Class

class ActivityTracker:
    """
    Polls active window every `poll_interval` seconds.
    Emits a record only when something meaningful changes (app OR title).
    """

    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._last_app     = None
        self._last_title   = None

    def get_current_activity(self) -> dict | None:
        info = get_active_window_info()
        app_name = info["app"]
        title    = info["title"]
        url      = info["url"]

        if app_name == self._last_app and title == self._last_title:
            return None

        self._last_app   = app_name
        self._last_title = title

        return {
            "app"      : app_name,
            "title"    : title,
            "url"      : url,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def wait(self):
        time.sleep(self.poll_interval)
