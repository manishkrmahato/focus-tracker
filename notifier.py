# notifier.py - Two-tier alert system. Cross-platform.
# TIER 1 (social media): fires EVERY time app is opened - no cooldown, no threshold.
# TIER 2 (YouTube/browser): fires after threshold, cooldown is PER-APP.

import time
import threading
import platform
import subprocess
import sys

OS = platform.system()

SOCIAL_MEDIA_APPS = {
    "whatsapp", "whatsapp.root", "instagram", "facebook", "messenger",
    "snapchat", "telegram", "discord", "tiktok", "twitter",
}


#Sound

def play_alert_sound():
    def _worker():
        try:
            if OS == "Windows":
                import winsound
                winsound.Beep(880,  300); time.sleep(0.08)
                winsound.Beep(1100, 300); time.sleep(0.08)
                winsound.Beep(880,  300)
            elif OS == "Darwin":
                subprocess.run(["afplay", "/System/Library/Sounds/Sosumi.aiff"],
                               capture_output=True, timeout=5)
            else:
                # Linux - try paplay, then aplay, then terminal bell
                for cmd in [
                    ["paplay", "/usr/share/sounds/alsa/Front_Center.wav"],
                    ["aplay",  "/usr/share/sounds/alsa/Front_Center.wav"],
                ]:
                    try:
                        subprocess.run(cmd, capture_output=True, timeout=5)
                        return
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue
                sys.stdout.write("\a\a\a"); sys.stdout.flush()
        except Exception:
            sys.stdout.write("\a\a\a"); sys.stdout.flush()

    threading.Thread(target=_worker, daemon=True).start()


#Popup

def show_popup(title: str, message: str, urgent: bool = False):
    border = "━" * 58
    icon   = "🚨" if urgent else "🔔"
    print(f"\n{border}\n  {icon}  {title}\n  {message}\n{border}\n")

    def _show():
        try:
            if OS == "Windows":
                import ctypes
                flags = (0x10 if urgent else 0x30) | 0x40000
                ctypes.windll.user32.MessageBoxW(0, message, title, flags)
            elif OS == "Darwin":
                script = (
                    f'display notification "{message}" with title "{title}" '
                    f'sound name "Sosumi"'
                )
                subprocess.run(["osascript", "-e", script],
                                capture_output=True, timeout=5)
            else:
                # Linux - try notify-send
                subprocess.run(
                    ["notify-send", title, message,
                     "--urgency", "critical" if urgent else "normal"],
                    capture_output=True, timeout=5
                )
        except Exception:
            pass  # terminal print above is always shown

    threading.Thread(target=_show, daemon=True).start()


#SmartNotifier

class SmartNotifier:
    """
    Two-tier notifier:
      Tier 1 - Social media: immediate alert every time app is opened.
      Tier 2 - Other distractions: alert after threshold, per-app cooldown.
    """

    def __init__(
        self,
        distraction_threshold_sec: int  = 15,
        cooldown_sec: int               = 45,
        confidence_threshold: float     = 0.65,
    ):
        self.threshold   = distraction_threshold_sec
        self.cooldown    = cooldown_sec
        self.conf_thresh = confidence_threshold

        self._distraction_start : dict[str, float] = {}
        self._last_alert        : dict[str, float] = {}
        self._current_app       : str              = ""
        self._alert_count       : int              = 0

        print(
            f"[Notifier] Ready - threshold={self.threshold}s | "
            f"cooldown={self.cooldown}s | min_confidence={self.conf_thresh:.0%}"
        )

    def update(
        self,
        category   : str,
        confidence : float,
        reason     : str,
        app        : str,
        title      : str,
    ):
        now     = time.time()
        app_key = app.lower().strip()

        if app_key != self._current_app:
            self._current_app = app_key

        if category != "DISTRACTION":
            if app_key in self._distraction_start:
                elapsed = int(now - self._distraction_start[app_key])
                print(f"[Notifier] '{app}' no longer distraction (was {elapsed}s)")
                del self._distraction_start[app_key]
            return

        if confidence < self.conf_thresh:
            print(f"[Notifier] Low conf ({confidence:.0%}) for '{app}' - skipping")
            return

        # Tier 1: Social media - fire every single time
        if app_key in SOCIAL_MEDIA_APPS:
            self._fire(app, title, reason, now, urgent=True,
                       duration_str="immediately")
            return

        # Tier 2: Threshold-based, timer keyed by APP not title
        if app_key not in self._distraction_start:
            self._distraction_start[app_key] = now
            print(
                f"[Notifier]  Timer started - '{app}' "
                f"({confidence:.0%}) [{reason}]"
            )
            return

        distracted_for = now - self._distraction_start[app_key]
        since_last     = now - self._last_alert.get(app_key, 0)

        if distracted_for < self.threshold:
            remaining = int(self.threshold - distracted_for)
            print(
                f"[Notifier]  '{app}' distracted {int(distracted_for)}s - "
                f"alert in {remaining}s [{reason}]"
            )
            return

        if since_last < self.cooldown:
            remaining = int(self.cooldown - since_last)
            print(f"[Notifier]  Cooldown for '{app}' - {remaining}s left")
            return

        m, s    = divmod(int(distracted_for), 60)
        dur_str = f"{m}m {s}s" if m else f"{s}s"
        self._fire(app, title, reason, now, urgent=False, duration_str=dur_str)
        self._last_alert[app_key] = now

    def _fire(
        self,
        app: str, title: str, reason: str,
        now: float, urgent: bool, duration_str: str
    ):
        self._alert_count += 1
        if urgent:
            msg = (
                f"You opened {app.title()} during study time!\n"
                f"Close this window and back to work!"
            )
            hdr = f"STOP! - {app.title()} Detected"
        else:
            msg = (
                f"Distracted for {duration_str} on '{app}'.\n"
                f"Window: {title[:55]}\n"
                f"Reason: {reason}"
            )
            hdr = f"Focus Alert #{self._alert_count} - Refocus!"

        play_alert_sound()
        show_popup(hdr, msg, urgent=urgent)
        print(
            f"[Notifier] {'🚨' if urgent else '🔔'} Alert #{self._alert_count} - "
            f"'{app}' ({duration_str})"
        )

    def reset(self):
        self._distraction_start.clear()
        self._last_alert.clear()
        self._current_app = ""
        self._alert_count = 0

    @property
    def alert_count(self) -> int:
        return self._alert_count
