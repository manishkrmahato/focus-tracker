# test_alerts.py - Manual component test script (run this directly, not pytest)
# Tests sound + popup + classifier on your actual machine.
# For automated tests use:  pytest tests/ -v

import time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\n" + "="*60)
print("   Focus Tracker v3.0 - Cross-Platform System Test")
print("="*60 + "\n")

import platform
print(f"Platform: {platform.system()} {platform.release()}\n")

#Test 1: Sound
print("TEST 1: Alert sound")
from notifier import play_alert_sound
play_alert_sound()
time.sleep(1)
print("  (check that you heard a beep - terminal bell if no speaker)\n")

# Test 2: Popup
print("TEST 2: Desktop popup")
from notifier import show_popup
show_popup("Focus Tracker Test", "Popup works! Close this.", urgent=False)
time.sleep(2)
print("  Popup fired (check your taskbar/notifications)\n")

#Test 3: Classifier
print("TEST 3: Context classifier accuracy (no ML model needed)")
from classifier import ContextClassifier
clf = ContextClassifier(ml_pipeline=None)

tests = [
    ("whatsapp.root", "WhatsApp",                                     "",                    "DISTRACTION"),
    ("chrome",        "Operating System Deadlock - YouTube",           "youtube.com",         "STUDY"),
    ("chrome",        "Funny Memes Compilation - YouTube",             "youtube.com",         "DISTRACTION"),
    ("chrome",        "Stack Overflow - Python",                       "stackoverflow.com",   "STUDY"),
    ("chrome",        "Instagram - Photos",                            "instagram.com",       "DISTRACTION"),
    ("code",          "main.py - VS Code",                             "",                    "STUDY"),
    ("chrome",        "Netflix - Watch TV",                            "netflix.com",         "DISTRACTION"),
    ("chrome",        "LeetCode - Two Sum",                            "leetcode.com",        "STUDY"),
    ("chrome",        "Spotify - Top Hits",                            "spotify.com",         "DISTRACTION"),
    ("chrome",        "GeeksforGeeks - DSA",                           "geeksforgeeks.org",   "STUDY"),
]

passed = 0
for app, title, url, expected in tests:
    label, conf, reason = clf.classify(app, title, url)
    ok = "✓" if label == expected else "✗"
    if label == expected:
        passed += 1
    print(f"  {ok} [{conf:.0%}] {app:<16} | {title[:35]:<35} -> {label}")
    if label != expected:
        print(f"       Expected {expected}, got {label}. Reason: {reason}")

print(f"\n  Score: {passed}/{len(tests)} correct\n")

#Test 4: SmartNotifier - immediate social media
print("TEST 4: Immediate social media alert (WhatsApp)")
from notifier import SmartNotifier
n = SmartNotifier(distraction_threshold_sec=15, cooldown_sec=60, confidence_threshold=0.5)
n.update("DISTRACTION", 1.0, "social media", "whatsapp.root", "WhatsApp")
time.sleep(0.5)
print(f"  Alerts fired: {n.alert_count}")
print(f"  {'✓' if n.alert_count == 1 else '✗'} Immediate alert {'worked' if n.alert_count == 1 else 'FAILED'}\n")

#Test 5: Reopen same app fires again
print("TEST 5: Reopening WhatsApp fires alert again (social media has no cooldown)")
n2 = SmartNotifier(distraction_threshold_sec=15, cooldown_sec=60, confidence_threshold=0.5)
n2.update("DISTRACTION", 1.0, "social media", "whatsapp.root", "WhatsApp")
time.sleep(0.3)
n2.update("STUDY", 0.9, "vscode", "code", "main.py")
time.sleep(0.3)
n2.update("DISTRACTION", 1.0, "social media", "whatsapp.root", "WhatsApp")
time.sleep(0.3)
print(f"  Alerts fired: {n2.alert_count} (expected 2)")
print(f"  {'✓' if n2.alert_count == 2 else '✗'} Reopen alert {'worked' if n2.alert_count == 2 else 'FAILED'}\n")

#Test 6: Demo replay smoke test
print("TEST 6: Demo replay (fast mode)")
from demo_replay import run_demo
from utils import SessionAnalytics

notifier3 = SmartNotifier(distraction_threshold_sec=1, cooldown_sec=1, confidence_threshold=0.5)
analytics3 = SessionAnalytics()
log_count = [0]

def dummy_log(ts, app, title, cat, dur):
    log_count[0] += 1

def dummy_print(act, cat, conf, reason, idx=None, total=None):
    pass

run_demo(
    classifier=clf, notifier=notifier3, analytics=analytics3,
    log_fn=dummy_log, print_row_fn=dummy_print, fast=True
)
print(f"  Demo replay: {log_count[0]} rows processed")
print(f"  {'✓' if log_count[0] > 0 else '✗'} Demo replay {'worked' if log_count[0] > 0 else 'FAILED'}\n")

print("="*60)
print(f"  All tests done.")
print(f"  If TEST 3 score >= 8/10 and TEST 4 shows ✓, system is ready.")
print(f"  Live tracking:  python main.py")
print(f"  Demo replay:    python main.py --demo")
print(f"  Pytest suite:   pytest tests/ -v")
print("="*60 + "\n")
