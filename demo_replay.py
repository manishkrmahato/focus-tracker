# demo_replay.py - Replays a pre-recorded CSV through the full classification
# and alert pipeline. Used by: python main.py --demo
# Can also be imported by test_alerts.py and pytest tests.

import csv
import time
from pathlib import Path
from typing import Iterator

BASE_DIR       = Path(__file__).parent
DEMO_CSV_PATH  = BASE_DIR / "demo_session.csv"

# Pre-recorded demo session
# Format: app, title, url, wait_sec
# This is embedded so the demo works even without a separate file.

DEMO_ROWS = [
    # app,             title,                                        url,                   wait_sec
    ("code",           "main.py - focus_tracker - VS Code",          "",                    2),
    ("chrome",         "Stack Overflow - Python dict comprehension",  "stackoverflow.com",   3),
    ("chrome",         "GeeksForGeeks - Binary Search Explained",    "geeksforgeeks.org",   3),
    ("chrome",         "LeetCode - Two Sum",                         "leetcode.com",        3),
    ("chrome",         "YouTube - Funny Cat Compilation",            "youtube.com",         2),
    ("chrome",         "YouTube - Meme Compilation 2024",            "youtube.com",         2),
    ("chrome",         "YouTube - Python Tutorial for Beginners",    "youtube.com",         3),
    ("chrome",         "Netflix - Watch TV Shows Online",            "netflix.com",         2),
    ("chrome",         "Instagram • Photos and Videos",              "instagram.com",       2),
    ("whatsapp",       "WhatsApp",                                   "",                    2),
    ("code",           "classifier.py - focus_tracker - VS Code",    "",                    3),
    ("chrome",         "Coursera - Machine Learning Specialization", "coursera.org",        3),
    ("chrome",         "Reddit - r/ProgrammerHumor",                 "reddit.com",          2),
    ("chrome",         "Spotify - Top Hits Playlist",                "spotify.com",         2),
    ("chrome",         "GitHub - focus_tracker/main.py",             "github.com",          3),
    ("chrome",         "Amazon.in - Buy Headphones",                 "amazon.in",           2),
    ("code",           "utils.py - focus_tracker - VS Code",         "",                    3),
    ("chrome",         "Claude - Google Chrome",                     "claude.ai",           3),
    ("chrome",         "YouTube - OS Scheduling Algorithms Lecture", "youtube.com",         3),
    ("chrome",         "Zomato - Order Food Online",                 "zomato.com",          2),
]


def load_demo_rows() -> list[dict]:
    """
    Returns the demo activity rows as a list of dicts.
    Loads from demo_session.csv if it exists, otherwise uses the built-in list.
    """
    if DEMO_CSV_PATH.exists():
        rows = []
        with open(DEMO_CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append({
                    "app"     : row["app"],
                    "title"   : row["title"],
                    "url"     : row.get("url", ""),
                    "wait_sec": float(row.get("wait_sec", 2)),
                })
        return rows

    return [
        {"app": r[0], "title": r[1], "url": r[2], "wait_sec": r[3]}
        for r in DEMO_ROWS
    ]


def iter_demo_activities(
    rows: list[dict],
    fast: bool = False
) -> Iterator[dict]:
    """
    Yields activity dicts from the demo rows.
    If fast=True, skips the wait (useful for tests).
    """
    for row in rows:
        if not fast:
            time.sleep(row["wait_sec"])
        yield {
            "app"      : row["app"],
            "title"    : row["title"],
            "url"      : row.get("url", ""),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }


def run_demo(
    classifier,
    notifier,
    analytics,
    log_fn,
    print_row_fn,
    fast: bool = False,
):
    """
    Full demo replay pipeline.
    Runs the same loop as main.py but feeds from DEMO_ROWS instead of live window.
    """
    rows = load_demo_rows()
    total = len(rows)

    print(f"\n[Demo] Replaying {total} pre-recorded activity records ...")
    if fast:
        print("[Demo] Fast mode - no delays\n")
    else:
        print("[Demo] Real-time pacing - watch the classification live!\n")

    last_rec  = None
    last_time = time.time()

    for i, act in enumerate(iter_demo_activities(rows, fast=fast), 1):
        now = time.time()

        # Finalise previous record
        if last_rec is not None:
            dur = now - last_time
            cat, _, _ = classifier.classify(
                last_rec["app"], last_rec["title"], last_rec.get("url", "")
            )
            analytics.record(cat, dur)
            log_fn(last_rec["timestamp"], last_rec["app"],
                   last_rec["title"], cat, dur)

        # Classify current
        cat, conf, reason = classifier.classify(
            act["app"], act["title"], act.get("url", "")
        )
        notifier.update(
            category=cat, confidence=conf, reason=reason,
            app=act["app"], title=act["title"]
        )

        print_row_fn(act, cat, conf, reason, i, total)

        last_rec  = act
        last_time = now

    # Finalise last
    if last_rec is not None:
        dur = time.time() - last_time
        cat, _, _ = classifier.classify(
            last_rec["app"], last_rec["title"], last_rec.get("url", "")
        )
        analytics.record(cat, dur)
        log_fn(last_rec["timestamp"], last_rec["app"],
               last_rec["title"], cat, dur)

    print("\n[Demo] Replay complete.\n")
