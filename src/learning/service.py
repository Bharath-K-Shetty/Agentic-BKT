"""Local-only quiz sessions and opt-in research export. No wallet or name needed."""
from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import time
from pathlib import Path

import pandas as pd

from src.learning.content import BANK_VERSION, BY_ID, QUESTIONS, SKILLS, public_question
from src.learning.tracing import bkt_predictions, dkt_predictions, load_checkpoint


class LearningService:
    def __init__(self, db_path, model_path=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.model, self.model_meta = None, None
        if model_path:
            self.model, self.model_meta = load_checkpoint(model_path)
            if self.model.n_skills != len(SKILLS):
                raise ValueError("Checkpoint skill count does not match the question bank")
            if self.model_meta["source"] != "synthetic" and self.model_meta["bank_version"] != BANK_VERSION:
                raise ValueError("Checkpoint question-bank version does not match")
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, consent INTEGER NOT NULL, condition TEXT NOT NULL,
                    created_at INTEGER NOT NULL, bank_version TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS answers (
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    question_id TEXT NOT NULL, skill_id INTEGER NOT NULL, correct INTEGER NOT NULL,
                    choice INTEGER NOT NULL, timestamp INTEGER NOT NULL, phase TEXT NOT NULL,
                    prediction REAL NOT NULL, predictor TEXT NOT NULL, lesson_seen INTEGER NOT NULL,
                    PRIMARY KEY(session_id, question_id)
                );
                CREATE TABLE IF NOT EXISTS lessons (
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    skill_id INTEGER NOT NULL, timestamp INTEGER NOT NULL
                );
            """)

    def connect(self):
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def start(self, consent=False):
        sid = secrets.token_urlsafe(24)
        condition = secrets.choice(["adaptive", "fixed"]) if consent else "adaptive"
        with self.connect() as db:
            db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
                       (sid, int(consent), condition, time.time_ns() // 1_000_000, BANK_VERSION))
        return self.state(sid)

    def _session(self, db, sid):
        session = db.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
        if session is None:
            raise KeyError("Session not found")
        return session

    def _history(self, db, sid):
        return [dict(r) for r in db.execute("SELECT * FROM answers WHERE session_id = ? ORDER BY timestamp", (sid,))]

    def _predictions(self, history, consent):
        # Synthetic-trained checkpoints can power an explicitly labeled demo only.
        if self.model is not None and (not consent or self.model_meta["source"] != "synthetic"):
            return dkt_predictions(self.model, history), "dkt", self.model_meta["source"]
        return bkt_predictions(history, len(SKILLS)), "bkt", "configured_demo_parameters"

    def _state(self, db, sid):
        session = self._session(db, sid)
        history = self._history(db, sid)
        probabilities, predictor, source = self._predictions(history, bool(session["consent"]))
        seen = {r["question_id"] for r in history}
        remaining = [q for q in QUESTIONS if q["id"] not in seen]
        question = None
        for phase in ["diagnostic", "practice", "assessment"]:
            candidates = [q for q in remaining if q["phase"] == phase]
            if candidates:
                if phase == "practice" and session["condition"] == "adaptive":
                    question = min(candidates, key=lambda q: (probabilities[q["skill_id"]], q["id"]))
                elif phase == "practice":
                    question = min(candidates, key=lambda q: (q["id"].endswith("-b"), q["skill_id"]))
                else:
                    question = min(candidates, key=lambda q: q["skill_id"])
                break
        progress = []
        for skill in SKILLS:
            responses = [r for r in history if r["skill_id"] == skill["id"]]
            progress.append({"id": skill["id"], "name": skill["name"], "probability": round(float(probabilities[skill["id"]]), 4),
                             "attempts": len(responses)})
        phase_scores = {}
        for phase in ["diagnostic", "practice", "assessment"]:
            rows = [r for r in history if r["phase"] == phase]
            total = sum(q["phase"] == phase for q in QUESTIONS)
            phase_scores[phase] = {"answered": len(rows), "correct": sum(r["correct"] for r in rows) if len(rows) == total or phase == "practice" else None,
                                   "total": total}
        result = {"session_id": sid, "consent": bool(session["consent"]), "condition": session["condition"],
                  "bank_version": BANK_VERSION, "answered": len(history), "total": len(QUESTIONS),
                  "phase": question["phase"] if question else "complete", "question": public_question(question) if question else None,
                  "skills": progress, "phase_scores": phase_scores, "predictor": predictor, "model_source": source,
                  "prediction_note": "Estimated chance of a correct response, not a validated measurement of mastery.",
                  "lesson": SKILLS[question["skill_id"]] if question and question["phase"] == "practice" else None}
        if question is None:
            result["review"] = [{"question": BY_ID[r["question_id"]]["prompt"], "correct": bool(r["correct"]),
                                  "explanation": BY_ID[r["question_id"]]["explanation"]} for r in history]
        return result

    def state(self, sid):
        with self.connect() as db:
            return self._state(db, sid)

    def answer(self, sid, question_id, choice):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db, sid)
            if state["question"] is None or question_id != state["question"]["id"]:
                raise ValueError("That question is not the current unanswered question. Refresh your session.")
            question = BY_ID[question_id]
            if isinstance(choice, bool) or not isinstance(choice, int) or not 0 <= choice < len(question["options"]):
                raise ValueError("Choose one of the available answers")
            history = self._history(db, sid)
            timestamp = max(time.time_ns() // 1_000_000, history[-1]["timestamp"] + 1 if history else 0)
            seen = db.execute("SELECT COUNT(*) FROM lessons WHERE session_id = ? AND skill_id = ?", (sid, question["skill_id"])).fetchone()[0]
            correct = int(choice == question["answer"])
            db.execute("INSERT INTO answers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (sid, question_id, question["skill_id"], correct, choice, timestamp, question["phase"],
                        state["skills"][question["skill_id"]]["probability"], state["predictor"], int(seen > 0)))
            result = self._state(db, sid)
            result["feedback"] = {"correct": bool(correct), "explanation": question["explanation"], "answer": question["answer"]} if question["phase"] == "practice" else {"recorded": True}
            return result

    def lesson(self, sid, skill_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = self._state(db, sid)
            if not state["lesson"] or state["lesson"]["id"] != skill_id:
                raise ValueError("This lesson is not the current recommendation")
            db.execute("INSERT INTO lessons VALUES (?, ?, ?)", (sid, skill_id, time.time_ns() // 1_000_000))
            return {"recorded": True}

    def delete(self, sid):
        with self.connect() as db:
            self._session(db, sid)
            db.execute("DELETE FROM sessions WHERE id = ?", (sid,))

    def export(self, output, completed_only=False):
        with self.connect() as db:
            # Export a separate pseudonym, never the bearer token used by the app.
            rows = pd.read_sql_query("""SELECT s.id, a.skill_id, a.correct, a.timestamp, a.question_id,
                a.phase, a.prediction, a.predictor, a.lesson_seen, s.condition, s.consent, s.bank_version
                FROM answers a JOIN sessions s ON a.session_id = s.id
                WHERE s.consent = 1 ORDER BY s.id, a.timestamp""", db)
        if len(rows):
            if completed_only:
                counts = rows.groupby("id").size()
                rows = rows[rows.id.isin(counts[counts == len(QUESTIONS)].index)].copy()
            mapping = {sid: f"learner-{i:04d}" for i, sid in enumerate(rows.id.unique(), 1)}
            rows.insert(0, "student_id", rows.id.map(mapping))
        else:
            rows.insert(0, "student_id", pd.Series(dtype=str))
        rows = rows.drop(columns="id")
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        rows.to_csv(output, index=False)
        return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Export opt-in learner records from the local HOMIE database")
    parser.add_argument("--db", type=Path, default=Path("data/processed/learning/sessions.sqlite3"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/learning/interactions.csv"))
    parser.add_argument("--completed-only", action="store_true", help="Include only sessions with all 20 answers")
    args = parser.parse_args()
    print(f"Exported {LearningService(args.db).export(args.output, args.completed_only)} consenting responses to {args.output}")


if __name__ == "__main__":
    main()
