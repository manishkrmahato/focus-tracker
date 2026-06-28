"""
test_classifier.py - Pytest tests for classifier.py
Run with:  pytest tests/ -v
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from classifier import ContextClassifier
from demo_replay import DEMO_ROWS, run_demo, load_demo_rows

@pytest.fixture(scope="module")
def clf():
    return ContextClassifier(ml_pipeline=None)


class TestDomains:

    def test_youtube_entertainment_is_distraction(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Funny Cat Compilation - YouTube", "youtube.com"
        )
        assert label == "DISTRACTION", f"Got {label}. Reason: {reason}"
        assert conf >= 0.60

    def test_youtube_educational_is_study(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Operating System Deadlock Explained - YouTube", "youtube.com"
        )
        assert label == "STUDY", f"Got {label}. Reason: {reason}"
        assert conf >= 0.60

    def test_leetcode_is_study(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Two Sum - LeetCode", "leetcode.com"
        )
        assert label == "STUDY", f"Got {label}. Reason: {reason}"

    def test_spotify_is_distraction(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Spotify - Top Hits Playlist", "spotify.com"
        )
        assert label == "DISTRACTION", f"Got {label}. Reason: {reason}"

    def test_netflix_is_distraction(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Netflix - Watch TV Shows Online", "netflix.com"
        )
        assert label == "DISTRACTION", f"Got {label}. Reason: {reason}"

    def test_stackoverflow_is_study(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "How to reverse a list in Python - Stack Overflow", "stackoverflow.com"
        )
        assert label == "STUDY", f"Got {label}. Reason: {reason}"

    def test_github_is_study(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "focus_tracker/main.py at main - GitHub", "github.com"
        )
        assert label == "STUDY", f"Got {label}. Reason: {reason}"

    def test_instagram_domain_is_distraction(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Instagram - Photos and Videos", "instagram.com"
        )
        assert label == "DISTRACTION", f"Got {label}. Reason: {reason}"

    def test_reddit_is_distraction(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Reddit - r/ProgrammerHumor", "reddit.com"
        )
        assert label == "DISTRACTION", f"Got {label}. Reason: {reason}"

    def test_geeksforgeeks_is_study(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "Binary Search Algorithm - GeeksforGeeks", "geeksforgeeks.org"
        )
        assert label == "STUDY", f"Got {label}. Reason: {reason}"


class TestSocialMediaApps:

    def test_whatsapp_app_is_distraction(self, clf):
        label, conf, reason = clf.classify("whatsapp", "WhatsApp", "")
        assert label == "DISTRACTION"
        assert conf == 1.0

    def test_whatsapp_root_is_distraction(self, clf):
        label, conf, _ = clf.classify("whatsapp.root", "WhatsApp", "")
        assert label == "DISTRACTION"
        assert conf == 1.0

    def test_instagram_app_is_distraction(self, clf):
        label, conf, _ = clf.classify("instagram", "Instagram", "")
        assert label == "DISTRACTION"
        assert conf == 1.0

    def test_telegram_app_is_distraction(self, clf):
        label, conf, _ = clf.classify("telegram", "Telegram", "")
        assert label == "DISTRACTION"
        assert conf == 1.0


class TestStudyApps:

    def test_vscode_is_study(self, clf):
        label, conf, reason = clf.classify("code", "main.py - focus_tracker - VS Code", "")
        assert label == "STUDY", f"Got {label}. Reason: {reason}"
        assert conf >= 0.90

    def test_pycharm_is_study(self, clf):
        label, conf, reason = clf.classify("pycharm", "classifier.py - PyCharm", "")
        assert label == "STUDY", f"Got {label}. Reason: {reason}"

    def test_jupyter_is_study(self, clf):
        label, conf, reason = clf.classify("jupyter", "Untitled - Jupyter Notebook", "")
        assert label == "STUDY", f"Got {label}. Reason: {reason}"


class TestConfidence:

    def test_social_media_confidence_is_one(self, clf):
        _, conf, _ = clf.classify("discord", "Discord", "")
        assert conf == 1.0

    def test_known_study_app_confidence_is_high(self, clf):
        _, conf, _ = clf.classify("code", "utils.py - VS Code", "")
        assert conf >= 0.90

    def test_study_domain_confidence_is_high(self, clf):
        _, conf, _ = clf.classify("chrome", "LeetCode Problem", "leetcode.com")
        assert conf >= 0.72

    def test_distraction_domain_confidence_is_high(self, clf):
        _, conf, _ = clf.classify("chrome", "Netflix", "netflix.com")
        assert conf >= 0.72


class TestEdgeCases:

    def test_unknown_app_returns_valid_label(self, clf):
        label, conf, reason = clf.classify("somerandombinary", "Some Window", "")
        assert label in ("STUDY", "DISTRACTION", "NEUTRAL")
        assert 0.0 <= conf <= 1.0
        assert isinstance(reason, str)

    def test_empty_inputs_do_not_crash(self, clf):
        label, conf, reason = clf.classify("", "", "")
        assert label in ("STUDY", "DISTRACTION", "NEUTRAL")

    def test_youtube_tutorial_is_study(self, clf):
        label, _, reason = clf.classify(
            "chrome", "Python Full Course Tutorial for Beginners - YouTube", "youtube.com"
        )
        assert label == "STUDY", f"Got {label}. Reason: {reason}"

    def test_youtube_no_keyword_is_classified(self, clf):
        label, conf, reason = clf.classify(
            "chrome", "My Upload - YouTube", "youtube.com"
        )
        assert label in ("STUDY", "DISTRACTION", "NEUTRAL")
        assert conf >= 0.0


class TestDemoReplay:

    def test_demo_rows_all_produce_valid_output(self, clf):
        for row in DEMO_ROWS:
            app, title, url, _ = row
            label, conf, reason = clf.classify(app, title, url)
            assert label in ("STUDY", "DISTRACTION", "NEUTRAL"), \
                f"Bad label '{label}' for app={app}"
            assert 0.0 <= conf <= 1.0
            assert isinstance(reason, str) and reason

    def test_demo_replay_runs_fast_without_errors(self, clf):
        from notifier import SmartNotifier
        from utils import SessionAnalytics

        notifier  = SmartNotifier(
            distraction_threshold_sec=1,
            cooldown_sec=1,
            confidence_threshold=0.5
        )
        analytics = SessionAnalytics()
        log_calls = []

        def dummy_log(ts, app, title, cat, dur):
            log_calls.append((app, cat))

        def dummy_print(act, cat, conf, reason, idx=None, total=None):
            pass

        run_demo(
            classifier   = clf,
            notifier     = notifier,
            analytics    = analytics,
            log_fn       = dummy_log,
            print_row_fn = dummy_print,
            fast         = True,
        )

        assert len(log_calls) == len(load_demo_rows())
        for app, cat in log_calls:
            assert cat in ("STUDY", "DISTRACTION", "NEUTRAL"), \
                f"Bad category '{cat}' for app={app}"
