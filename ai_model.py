# ai_model.py - Hybrid ML model: TF-IDF + Logistic Regression
# Used as the FALLBACK when rule-based classifier is uncertain (confidence < 0.70)

import os, re, pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset.csv")
MODEL_PATH   = os.path.join(BASE_DIR, "model.pkl")


def preprocess(text: str) -> str:
    if not text or not isinstance(text, str):
        return "unknown"
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "unknown"


def train_model():
    print("[AI Model] Training on dataset.csv ...")
    df = pd.read_csv(DATASET_PATH).dropna(subset=["text","label"])
    df["text"] = df["text"].apply(preprocess)

    X, y = df["text"].tolist(), df["label"].tolist()
    print(f"[AI Model] {len(X)} samples | classes: {sorted(set(y))}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1,2), max_features=8000, sublinear_tf=True)),
        ("clf",   LogisticRegression(max_iter=1000, C=1.5, solver="lbfgs")),
    ])
    pipeline.fit(X_train, y_train)

    acc = accuracy_score(y_test, pipeline.predict(X_test))
    print(f"[AI Model] Accuracy: {acc*100:.1f}%")
    print(classification_report(y_test, pipeline.predict(X_test)))

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(pipeline, f)
    print(f"[AI Model] Saved -> {MODEL_PATH}")
    return pipeline


def load_model():
    if not os.path.exists(MODEL_PATH):
        print("[AI Model] model.pkl not found - training now ...")
        return train_model()
    with open(MODEL_PATH, "rb") as f:
        m = pickle.load(f)
    print("[AI Model] Loaded model.pkl")
    return m


def ml_classify(pipeline, text: str) -> tuple[str, float]:
    """
    Returns (label, confidence) using the ML model.
    label: STUDY | DISTRACTION | NEUTRAL
    confidence: probability of predicted class
    """
    cleaned = preprocess(text)
    proba   = pipeline.predict_proba([cleaned])[0]
    classes = pipeline.classes_
    idx     = proba.argmax()
    return classes[idx], float(proba[idx])


if __name__ == "__main__":
    train_model()
