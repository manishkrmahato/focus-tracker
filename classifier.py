# classifier.py - Rule-based + ML Hybrid Classifier
#
# Decision flow:
#   1. Social media app?          - DISTRACTION (confidence 1.0, immediate)
#   2. YouTube? - score title     - rule-based (high confidence)
#   3. Browser? - check domain    - rule-based (high confidence)
#   4. Known study/code app?      - STUDY (high confidence)
#   5. Rule-based keyword score   - if confidence >= 0.72 - use it
#   6. ML model fallback          - used when rules are uncertain
#
# This means the system becomes MORE general over time as you add rows to dataset.csv

import re
from urllib.parse import urlparse

#Social media - ALWAYS distraction, fires immediately
SOCIAL_MEDIA_APPS = {
    "whatsapp", "whatsapp.root", "instagram", "facebook", "messenger",
    "snapchat", "telegram", "discord", "tiktok", "twitter",
    "com.whatsapp", "com.instagram.android", "com.facebook.katana",
}

#Study/coding apps - always STUDY regardless of title
STUDY_APPS = {
    "code", "vscode", "pycharm", "intellij", "eclipse", "notepad++",
    "sublime", "atom", "vim", "nvim", "emacs", "jupyter", "spyder",
    "anaconda", "rstudio", "matlab", "terminal", "cmd", "powershell",
    "bash", "mysql", "dbeaver", "postman", "insomnia", "figma",
    "obsidian", "anki", "zotero", "mendeley", "overleaf",
}

#Browsers
BROWSERS = {"chrome", "firefox", "msedge", "opera", "brave", "edge", "iexplore", "chromium"}

#Study domains
STUDY_DOMAINS = {
    "github.com", "stackoverflow.com", "docs.python.org",
    "developer.mozilla.org", "w3schools.com", "geeksforgeeks.org",
    "leetcode.com", "hackerrank.com", "codechef.com", "codeforces.com",
    "kaggle.com", "arxiv.org", "coursera.org", "edx.org", "udemy.com",
    "khanacademy.org", "brilliant.org", "nptel.ac.in", "mit.edu",
    "stanford.edu", "replit.com", "colab.research.google.com",
    "overleaf.com", "wikipedia.org", "docs.microsoft.com",
    "learn.microsoft.com", "cloud.google.com", "aws.amazon.com",
    "tensorflow.org", "pytorch.org", "scikit-learn.org",
    "freecodecamp.org", "dev.to", "towardsdatascience.com", "medium.com",
    "jupyter.org", "anaconda.com", "claude.ai", "chat.openai.com",
    "bard.google.com", "notion.so", "trello.com",
}

#Distraction domains
DISTRACTION_DOMAINS = {
    "instagram.com", "facebook.com", "twitter.com", "x.com",
    "reddit.com", "9gag.com", "buzzfeed.com", "tiktok.com",
    "netflix.com", "primevideo.com", "hotstar.com", "disneyplus.com",
    "gaana.com", "jiosaavn.com", "wynk.in",
    "amazon.in", "flipkart.com", "myntra.com", "snapdeal.com", "meesho.com",
    "zomato.com", "swiggy.com", "cricbuzz.com", "espncricinfo.com",
    "twitch.tv", "discord.com", "spotify.com","whatsapp.com", "snapchat.com",
    "sharechat.com", "mxtakataka.com", "roposo.com",
}

NEUTRAL_DOMAINS = {
    "spotify.com", "open.spotify.com",
}

#YouTube keyword lists
YT_STUDY = [
    "OS","tutorial", "lecture", "course", "lesson", "learn", "study", "explained",
    "explanation", "algorithm", "data structure", "programming", "coding",
    "python", "java", "javascript", "c++", "machine learning", "deep learning",
    "neural network", "artificial intelligence", "operating system", "dbms",
    "computer network", "mathematics", "calculus", "linear algebra", "physics",
    "chemistry", "biology", "engineering", "science", "research", "thesis",
    "how to", "problem solving", "interview prep", "placement",
    "competitive programming", "dsa", "web dev", "sql", "database",
    "cloud", "docker", "kubernetes", "react", "node", "full stack",
    "backend", "frontend", "system design", "os concepts", "networking",
    "cybersecurity", "ethical hacking", "blockchain", "mit", "stanford",
    "nptel", "khan academy", "coursera", "edx", "gate exam", "semester",
    "revision", "concept", "theory", "proof", "derivation", "formula",
]

YT_DISTRACTION = [
    "funny", "meme", "prank", "vlog", "roast", "challenge", "reaction",
    "shorts", "reels", "entertainment", "comedy", "fail", "compilation",
    "music video", "song", "rap", "dance", "gossip", "celebrity",
    "gaming", "gameplay", "stream", "highlights", "match", "cricket",
    "ipl", "football", "movie", "trailer", "web series", "episode",
    "unboxing", "haul", "shopping", "fashion", "makeup", "food",
    "travel", "asmr", "satisfying", "drama", "viral", "trending",
    "tiktok", "twitch", "podcast", "bhoot", "horror", "romantic",
    "love story", "fight", "news", "breaking", "gossip", "award",
    "performance", "live concert", "stand up", "roast", "prank",
]

#General title keywords
STUDY_TITLE_KW = [
    "visual studio", "vscode", "vs code", "pycharm", "intellij", "eclipse",
    "jupyter", "notebook", "anaconda", "terminal", "cmd", "powershell",
    "stackoverflow", "github", "leetcode", "hackerrank", "geeksforgeeks",
    "coursera", "edx", "nptel", "khanacademy", "udemy",
    "pdf", "document", "report", "thesis", "assignment", "notes",
    "word", "excel", "powerpoint", "docs", "sheets",
    "calculator", "desmos", "wolfram", "matlab",
    "tutorial", "lecture", "course", "algorithm", "programming",
    "dataset", "machine learning", "deep learning", "research",
]

DIST_TITLE_KW = [
    "youtube", "instagram", "facebook", "whatsapp", "twitter", "tiktok",
    "netflix", "amazon prime", "hotstar", "spotify",
    "funny", "meme", "shorts", "reels", "vlog", "gaming",
    "cricket", "ipl", "football", "match", "live score",
    "shopping", "amazon", "flipkart", "myntra", "zomato", "swiggy",
    "news feed", "trending", "viral", "entertainment", "trailer",
    "song", "music video", "episode", "series", "movie",
]


class ContextClassifier:
    """
    Rule-based + ML hybrid.
    Pass `ml_pipeline=None` to run rules only (no ML fallback).
    Pass `ml_pipeline=<trained model>` to enable ML fallback for uncertain cases.
    """

    RULE_CONFIDENCE_THRESHOLD = 0.72   # below this -> hand off to ML

    def __init__(self, ml_pipeline=None):
        self.ml = ml_pipeline

    def classify(
        self, app: str, title: str, url: str = ""
    ) -> tuple[str, float, str]:
        """
        Returns (label, confidence, reason).
        label: STUDY | DISTRACTION | NEUTRAL
        """
        app_c   = app.lower().strip()
        title_c = title.lower().strip()
        url_c   = url.lower().strip()

        #Rule 1: Social media, always immediate distraction
        if self._is_social_media(app_c, title_c):
            return ("DISTRACTION", 1.0,
                    f"Social media - always distraction")

        #Rule 2: YouTube, classify by titl
        if self._is_youtube(app_c, title_c, url_c):
            label, conf, reason = self._classify_youtube(title_c)
            if conf >= self.RULE_CONFIDENCE_THRESHOLD:
                return label, conf, reason
            # Low confidence -> try ML on the full title
            return self._ml_or_neutral(title, f"YouTube (low conf rule: {reason})")

        #Rule 3: Browser, domain lookup
        if self._is_browser(app_c):
            label, conf, reason = self._classify_browser(title_c, url_c)
            if conf >= self.RULE_CONFIDENCE_THRESHOLD:
                return label, conf, reason
            return self._ml_or_neutral(title, f"Browser (low conf rule: {reason})")

        #Rule 4: Known study/coding app
        if any(sa in app_c for sa in STUDY_APPS):
            return ("STUDY", 0.95, f"Known study/coding app '{app}'")

        #Rule 5: General keyword score
        label, conf, reason = self._keyword_score(title_c, app_c)
        if conf >= self.RULE_CONFIDENCE_THRESHOLD:
            return label, conf, reason

        #Rule 6: ML fallback
        return self._ml_or_neutral(f"{app} {title}", f"ML fallback (rules: {reason})")

    #Helpers

    def _is_social_media(self, app: str, title: str) -> bool:
        if app in SOCIAL_MEDIA_APPS:
            return True
        social = ["whatsapp", "instagram", "facebook", "snapchat",
                "telegram", "discord", "tiktok"]
        return any(w in title for w in social) and \
            not any(k in title for k in STUDY_TITLE_KW)

    def _is_youtube(self, app: str, title: str, url: str) -> bool:
        return ("youtube" in url or "youtu.be" in url or
                ("youtube" in title and "vscode" not in app))

    def _classify_youtube(self, title: str) -> tuple[str, float, str]:
        sh = [k for k in YT_STUDY if k in title]
        dh = [k for k in YT_DISTRACTION if k in title]

        if not sh and not dh:
            return ("DISTRACTION", 0.75, "YouTube default distraction")

        total = len(sh) + len(dh)
        if len(sh) > len(dh):
            conf = min(0.95, 0.60 + (len(sh)/total)*0.35)
            return ("STUDY", conf,
                    f"YouTube study (matched: {', '.join(sh[:3])})")
        else:
            conf = min(0.95, 0.60 + (len(dh)/total)*0.35)
            return ("DISTRACTION", conf,
                    f"YouTube distraction (matched: {', '.join(dh[:3])})")

    def _is_browser(self, app: str) -> bool:
        return any(b in app for b in BROWSERS)

    def _classify_browser(self, title: str, url: str) -> tuple[str, float, str]:
        domain = self._extract_domain(url or title)
        if domain:
            if any(nd in domain for nd in NEUTRAL_DOMAINS):
                return ("NEUTRAL", 0.90, f"Neutral domain: {domain}")
            if any(sd in domain for sd in STUDY_DOMAINS):
                return ("STUDY", 0.93, f"Study domain: {domain}")
            if any(dd in domain for dd in DISTRACTION_DOMAINS):
                return ("DISTRACTION", 0.93, f"Distraction domain: {domain}")
        return self._keyword_score(title, "browser")

    def _extract_domain(self, text: str) -> str:
        try:
            if not text.startswith("http"):
                text = "https://" + text
            return urlparse(text).netloc.replace("www.", "")
        except Exception:
            return ""

    def _keyword_score(self, title: str, app: str) -> tuple[str, float, str]:
        sh = [k for k in STUDY_TITLE_KW if k in title]
        dh = [k for k in DIST_TITLE_KW if k in title]

        if not sh and not dh:
            return ("NEUTRAL", 0.50, "No keywords matched")

        total = len(sh) + len(dh)
        if len(sh) >= len(dh):
            conf = min(0.90, 0.55 + (len(sh)/total)*0.35)
            return ("STUDY", conf,
                    f"Keywords: {', '.join(sh[:3])}")
        else:
            conf = min(0.90, 0.55 + (len(dh)/total)*0.35)
            return ("DISTRACTION", conf,
                    f"Keywords: {', '.join(dh[:3])}")

    def _ml_or_neutral(self, text: str, fallback_reason: str) -> tuple[str, float, str]:
        if self.ml is not None:
            try:
                from ai_model import ml_classify, preprocess
                label, conf = ml_classify(self.ml, text)
                return (label, conf, f"ML model ({fallback_reason})")
            except Exception as e:
                pass
        return ("NEUTRAL", 0.50, fallback_reason)
