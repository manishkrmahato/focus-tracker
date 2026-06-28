# main.py - AI Focus Tracker v3.0
# Rule-based + ML hybrid. Cross-platform. Supports --demo flag.
#
# Usage:
#   python main.py           - live tracking (your real windows)
#   python main.py --demo    - replay pre-recorded session (no window access needed)

import argparse
import time
import signal
import sys

from tracker    import ActivityTracker
from classifier import ContextClassifier
from notifier   import SmartNotifier
from utils      import init_log, log_activity, SessionAnalytics
from ai_model   import load_model

#Config
POLL_INTERVAL_SEC         = 2
DISTRACTION_THRESHOLD_SEC = 15
ALERT_COOLDOWN_SEC        = 45
CONFIDENCE_THRESHOLD      = 0.65
SUGGESTION_INTERVAL_SEC   = 300

#ANSI
R="\033[0m"; B="\033[1m"; G="\033[92m"; RED="\033[91m"
Y="\033[93m"; C="\033[96m"; GR="\033[90m"; M="\033[95m"
CAT = {"STUDY": G, "DISTRACTION": RED, "NEUTRAL": Y}

def ccat(cat):
    return f"{CAT.get(cat,R)}{B}{cat}{R}"

def cbar(c):
    f = int(c * 10)
    return f"[{'█'*f}{'░'*(10-f)}] {c:.0%}"

#Shutdown
_running = True
def _stop(s, f):
    global _running
    print(f"\n{C}[Main] Stopping ...{R}")
    _running = False
signal.signal(signal.SIGINT,  _stop)
signal.signal(signal.SIGTERM, _stop)


#Shared row printer

def print_row(act, cat, conf, reason, idx=None, total=None):
    ts  = act["timestamp"][11:]
    ap  = act["app"][:14]
    ttl = act["title"][:32]
    prefix = f"[{idx:>2}/{total}]" if idx and total else "      "
    print(
        f"  {GR}{prefix} {ts}{R}  {C}{ap:<16}{R}  "
        f"{ccat(cat):<23}  {M}{cbar(conf)}{R}  {GR}{ttl}{R}"
    )
    if cat == "DISTRACTION":
        print(f"  {GR}{'':>18} ↳ {reason}{R}")


#Header

def print_header(demo: bool):
    mode = "DEMO REPLAY" if demo else "Live Tracking"
    print(f"\n{B}{C}{'═'*70}{R}")
    print(f"{B}{C}  AI Focus Tracker v3.0 - Rule-Based + ML Hybrid  [{mode}]{R}")
    print(f"{B}{C}{'═'*70}{R}\n")


#Live tracking loop

def run_live(classifier, tracker, notifier, analytics):
    print(f"{G}[Main] Tracking live windows - open YouTube/WhatsApp to test!{R}")
    print(f"{GR}       Social media -> immediate | Others -> {DISTRACTION_THRESHOLD_SEC}s threshold{R}\n")
    print(f"{'─'*70}")
    print(f"  {'':6} {'TIME':<10} {'APP':<16} {'CAT':<14} {'CONFIDENCE':<18} TITLE")
    print(f"{'─'*70}")

    last_rec  = None
    last_time = time.time()
    last_sug  = time.time()

    while _running:
        act = tracker.get_current_activity()

        if act is not None:
            now = time.time()

            if last_rec is not None:
                dur = now - last_time
                pc, _, _ = classifier.classify(
                    last_rec["app"], last_rec["title"], last_rec.get("url","")
                )
                analytics.record(pc, dur)
                log_activity(last_rec["timestamp"], last_rec["app"],
                             last_rec["title"], pc, dur)

            cat, conf, reason = classifier.classify(
                act["app"], act["title"], act.get("url","")
            )
            notifier.update(
                category=cat, confidence=conf, reason=reason,
                app=act["app"], title=act["title"]
            )
            print_row(act, cat, conf, reason)

            last_rec  = act
            last_time = now

        if time.time() - last_sug >= SUGGESTION_INTERVAL_SEC:
            s = analytics.get_suggestion()
            if s:
                print(f"\n  {Y}{s}{R}\n")
            last_sug = time.time()

        tracker.wait()

    # Finalise last record
    if last_rec is not None:
        dur = time.time() - last_time
        cat, _, _ = classifier.classify(
            last_rec["app"], last_rec["title"], last_rec.get("url","")
        )
        analytics.record(cat, dur)
        log_activity(last_rec["timestamp"], last_rec["app"],
                     last_rec["title"], cat, dur)


#Main

def main():
    parser = argparse.ArgumentParser(
        description="AI Focus Tracker - track study vs distraction time."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Replay a pre-recorded activity CSV instead of reading live windows. "
             "Great for CI, presentations, and machines without display access.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="In --demo mode, skip all wait times (instant replay). Used in CI.",
    )
    args = parser.parse_args()

    print_header(demo=args.demo)
    init_log()

    print("[Main] Loading ML model ...")
    ml_pipeline = load_model()

    classifier = ContextClassifier(ml_pipeline=ml_pipeline)
    notifier   = SmartNotifier(
        distraction_threshold_sec = DISTRACTION_THRESHOLD_SEC,
        cooldown_sec              = ALERT_COOLDOWN_SEC,
        confidence_threshold      = CONFIDENCE_THRESHOLD,
    )
    analytics  = SessionAnalytics()

    if args.demo:
        from demo_replay import run_demo
        print(f"\n{Y}[Demo] Running pre-recorded session replay ...{R}")
        print(f"{GR}       Pass --fast to skip delays (used in CI){R}\n")
        print(f"{'─'*70}")
        print(f"  {'IDX':^6} {'TIME':<10} {'APP':<16} {'CAT':<14} {'CONFIDENCE':<18} TITLE")
        print(f"{'─'*70}")

        run_demo(
            classifier  = classifier,
            notifier    = notifier,
            analytics   = analytics,
            log_fn      = log_activity,
            print_row_fn= print_row,
            fast        = args.fast,
        )
    else:
        tracker = ActivityTracker(poll_interval=POLL_INTERVAL_SEC)
        run_live(classifier, tracker, notifier, analytics)

    sug = analytics.get_suggestion()
    if sug:
        print(f"\n  {Y}{sug}{R}")

    analytics.print_summary()
    print(f"{C}[Main] Log -> activity_log.csv | Goodbye!{R}\n")


if __name__ == "__main__":
    main()
