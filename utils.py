# utils.py
# Helper utilities: CSV logging, session analytics, smart suggestions.

import os
import csv
import time
from collections import deque
from datetime import datetime

#Paths
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_PATH  = os.path.join(BASE_DIR, "activity_log.csv")

LOG_HEADER = ["timestamp", "app", "title", "category", "duration_sec"]


#CSV Logger

def init_log():
    """Create activity_log.csv with header row if it doesn't exist yet."""
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(LOG_HEADER)
        print(f"[Logger] Log file created -> {LOG_PATH}")


def log_activity(timestamp: str, app: str, title: str,
                 category: str, duration_sec: float):
    """Append one row to activity_log.csv."""
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, app, title[:120], category,
                         round(duration_sec, 1)])


#Session Analytics

class SessionAnalytics:
    """
    Accumulates per-session statistics:
      • study / distraction / neutral seconds
      • distraction event count
      • rolling window for smart suggestions
    """

    def __init__(self):
        self.study_time       : float = 0.0
        self.distraction_time : float = 0.0
        self.neutral_time     : float = 0.0
        self.distraction_count: int   = 0

        self._session_start   : float = time.time()

        # Rolling window: stores (timestamp, category) for last 10 minutes
        self._window_minutes  : int   = 10
        self._recent_events   : deque = deque()

        # Track state for counting *new* distraction episodes
        self._last_category   : str | None = None

    #Update

    def record(self, category: str, duration_sec: float):
        """Call this every time an activity record is finalised."""
        if category == "STUDY":
            self.study_time += duration_sec
        elif category == "DISTRACTION":
            self.distraction_time += duration_sec
            # Count only when transitioning *into* distraction
            if self._last_category != "DISTRACTION":
                self.distraction_count += 1
        else:
            self.neutral_time += duration_sec

        self._last_category = category

        # Store in rolling window
        self._recent_events.append((time.time(), category))
        self._prune_window()

    #Metrics

    @property
    def total_time(self) -> float:
        return self.study_time + self.distraction_time + self.neutral_time

    @property
    def focus_score(self) -> float:
        """(Study time / Total time) * 100.  Returns 0 if no data yet."""
        total = self.total_time
        return round((self.study_time / total) * 100, 1) if total > 0 else 0.0

    @property
    def session_duration(self) -> float:
        return time.time() - self._session_start

    #Smart Suggestions

    def get_suggestion(self) -> str | None:
        """
        Analyse the rolling window and return a helpful suggestion string,
        or None if everything looks fine.
        """
        self._prune_window()
        events = list(self._recent_events)

        if not events:
            return None

        distraction_events = [e for e in events if e[1] == "DISTRACTION"]
        distraction_ratio  = len(distraction_events) / len(events)

        # Rule 1: Heavy distraction in window
        if distraction_ratio > 0.6 and len(events) >= 5:
            return (
                f"⚠️  You've been distracted {len(distraction_events)} times "
                f"in the last {self._window_minutes} minutes. "
                "Consider a short break and then refocus!"
            )

        # Rule 2: Long unbroken study - recommend a break
        if self.study_time > 3600 and self.distraction_time < 60:
            return (
                "🎉 You've studied for over an hour non-stop - great work! "
                "A 5-minute break will help consolidate memory."
            )

        # Rule 3: Distraction count milestone
        if self.distraction_count > 0 and self.distraction_count % 5 == 0:
            return (
                f"📊 You've been distracted {self.distraction_count} times "
                "this session. Try the Pomodoro technique: 25 min focus, "
                "5 min break."
            )

        return None

    #Session Summary

    def print_summary(self):
        """Print a formatted session summary to the terminal."""
        def fmt(seconds: float) -> str:
            m, s = divmod(int(seconds), 60)
            h, m = divmod(m, 60)
            if h:
                return f"{h}h {m}m {s}s"
            return f"{m}m {s}s" if m else f"{s}s"

        total   = self.total_time
        elapsed = self.session_duration

        print("\n" + "═" * 55)
        print("  📊  SESSION SUMMARY")
        print("═" * 55)
        print(f"  Session duration    : {fmt(elapsed)}")
        print(f"  Tracked activity    : {fmt(total)}")
        print(f"  ── Study time       : {fmt(self.study_time)}")
        print(f"  ── Distraction time : {fmt(self.distraction_time)}")
        print(f"  ── Neutral time     : {fmt(self.neutral_time)}")
        print(f"  Focus score         : {self.focus_score}%")
        print(f"  Distraction count   : {self.distraction_count}")

        # Grade
        score = self.focus_score
        if   score >= 80: grade = "🏆 Excellent - Keep it up!"
        elif score >= 60: grade = "👍 Good - Room to improve."
        elif score >= 40: grade = "⚠️  Fair - Try to stay focused."
        else:             grade = "❌ Poor - Work on your focus."
        print(f"  Performance grade   : {grade}")
        print("═" * 55 + "\n")

    #Internal

    def _prune_window(self):
        """Remove events older than the rolling window from the deque."""
        cutoff = time.time() - (self._window_minutes * 60)
        while self._recent_events and self._recent_events[0][0] < cutoff:
            self._recent_events.popleft()


#Misc Helpers

def format_seconds(seconds: float) -> str:
    """Convert raw seconds into a human-readable 'Xm Ys' string."""
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s}s" if m else f"{s}s"
