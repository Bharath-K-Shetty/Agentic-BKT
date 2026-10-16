"""Local instrumented decision environment. No transaction is constructed or sent."""
import json
import math
import secrets
import time
from pathlib import Path

import pandas as pd

from src.learning.content import SKILLS
from src.learning.service import LearningService
from src.learning.scenarios import BANKS, BY_ID, VERSION, public_scenario, score
from src.learning.tracing import bkt_predictions


class SimulatorService(LearningService):
    def __init__(self, db_path):
        super().__init__(db_path)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS sim_sessions (id TEXT PRIMARY KEY, consent INTEGER NOT NULL,
                condition TEXT NOT NULL, version TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sim_runs (session_id TEXT REFERENCES sim_sessions(id) ON DELETE CASCADE,
                scenario_id TEXT NOT NULL, started_at INTEGER NOT NULL, prediction REAL NOT NULL,
                PRIMARY KEY(session_id, scenario_id));
            CREATE TABLE IF NOT EXISTS sim_events (session_id TEXT REFERENCES sim_sessions(id) ON DELETE CASCADE,
                scenario_id TEXT NOT NULL, kind TEXT NOT NULL, value TEXT NOT NULL, timestamp INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS sim_answers (session_id TEXT REFERENCES sim_sessions(id) ON DELETE CASCADE,
                scenario_id TEXT NOT NULL, skill_id INTEGER NOT NULL, correct INTEGER NOT NULL,
                action TEXT NOT NULL, reason INTEGER NOT NULL, setting REAL, timestamp INTEGER NOT NULL,
                inspection_count INTEGER NOT NULL, hint_count INTEGER NOT NULL, revision_count INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL, phase TEXT NOT NULL, prediction REAL NOT NULL,
                PRIMARY KEY(session_id, scenario_id));
            """)

    def start(self, consent=False):
        sid = secrets.token_urlsafe(24)
        with self.connect() as db:
            db.execute("INSERT INTO sim_sessions VALUES (?, ?, ?, ?)", (sid, int(consent), secrets.choice(["adaptive", "fixed"]) if consent else "adaptive", VERSION))
        return self.state(sid)

    def _state(self, db, sid):
        session = db.execute("SELECT * FROM sim_sessions WHERE id = ?", (sid,)).fetchone()
        if session is None:
            raise KeyError("Session not found")
        if session["version"] not in BANKS:
            raise ValueError("Unsupported simulator bank version")
        bank = BANKS[session["version"]]
        history = [dict(r) for r in db.execute("SELECT * FROM sim_answers WHERE session_id = ? ORDER BY timestamp", (sid,))]
        # Transfer outcomes must not affect the policy or reveal assessment scores.
        probabilities = bkt_predictions([r for r in history if r["phase"] != "transfer"], len(SKILLS))
        seen = {r["scenario_id"] for r in history}
        current = None
        # Once offered, a scenario stays current even if a model changes.
        active = db.execute("SELECT scenario_id FROM sim_runs WHERE session_id = ? AND scenario_id NOT IN (SELECT scenario_id FROM sim_answers WHERE session_id = ?) ORDER BY started_at LIMIT 1", (sid, sid)).fetchone()
        if active:
            current = BY_ID[active["scenario_id"]]
        else:
            for phase in ["diagnostic", "practice", "transfer"]:
                available = [s for s in bank if s["phase"] == phase and s["id"] not in seen]
                if available:
                    current = min(available, key=lambda s: (probabilities[s["skill_id"]] if phase == "practice" and session["condition"] == "adaptive" else s["skill_id"], s["skill_id"], s["id"]))
                    db.execute("INSERT INTO sim_runs VALUES (?, ?, ?, ?)", (sid, current["id"], time.time_ns() // 1_000_000, float(probabilities[current["skill_id"]])))
                    break
        events = [] if current is None else [dict(e) for e in db.execute("SELECT kind, value, timestamp FROM sim_events WHERE session_id = ? AND scenario_id = ? ORDER BY timestamp, rowid", (sid, current["id"]))]
        inspected = {e["value"] for e in events if e["kind"] == "inspect"}
        result = {"session_id": sid, "consent": bool(session["consent"]), "condition": session["condition"], "version": session["version"],
                  "answered": len(history), "total": len(bank), "scenario": public_scenario(current) if current else None,
                  "inspected": [e for e in current["evidence"] if e["id"] in inspected] if current else [],
                  "decision": json.loads(next((e["value"] for e in reversed(events) if e["kind"] == "revise"), "null")),
                  "hint": current["hint"] if current and any(e["kind"] == "hint" for e in events) else None,
                  "skills": [] if current and current["phase"] != "practice" else [{"name": s["name"], "probability": float(probabilities[s["id"]])} for s in SKILLS],
                  "predictor": "Configured BKT baseline; behavior-augmented DKT is evaluated offline, not validated for live coaching."}
        if not current:
            result["review"] = [{"title": BY_ID[r["scenario_id"]]["title"], "phase": r["phase"], "correct": bool(r["correct"]),
                                 "action": r["action"], "feedback": BY_ID[r["scenario_id"]]["feedback"],
                                 "inspection_count": r["inspection_count"], "revision_count": r["revision_count"], "hint_count": r["hint_count"]} for r in history]
            result["scores"] = {phase: {"correct": sum(r["correct"] for r in history if r["phase"] == phase),
                                        "total": sum(s["phase"] == phase for s in bank)} for phase in ["diagnostic", "practice", "transfer"] if any(s["phase"] == phase for s in bank)}
        return result

    def _current(self, db, sid, scenario_id):
        state = self._state(db, sid)
        if not state["scenario"] or state["scenario"]["id"] != scenario_id:
            raise ValueError("That is not the current unanswered scenario")
        return BY_ID[scenario_id]

    def inspect(self, sid, scenario_id, card_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            scenario = self._current(db, sid, scenario_id)
            if card_id not in {e["id"] for e in scenario["evidence"]}:
                raise ValueError("Unknown evidence card")
            db.execute("INSERT INTO sim_events VALUES (?, ?, 'inspect', ?, ?)", (sid, scenario_id, card_id, time.time_ns() // 1_000_000))
            return self._state(db, sid)

    def hint(self, sid, scenario_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            scenario = self._current(db, sid, scenario_id)
            if scenario["phase"] != "practice":
                raise ValueError("Hints are available only during practice")
            db.execute("INSERT INTO sim_events VALUES (?, ?, 'hint', '', ?)", (sid, scenario_id, time.time_ns() // 1_000_000))
            return self._state(db, sid)

    def _decision(self, scenario, action, reason, setting):
        if action not in scenario["actions"] or isinstance(reason, bool) or not isinstance(reason, int) or not 0 <= reason < len(scenario["reasons"]):
            raise ValueError("Select a valid action and reasoning")
        spec = scenario["setting"]
        if spec and (isinstance(setting, bool) or not isinstance(setting, (int, float)) or not math.isfinite(setting) or not spec["min"] <= setting <= spec["max"]):
            raise ValueError("Set an execution value within the displayed range")
        if not spec and setting is not None:
            raise ValueError("This scenario has no editable execution value")
        return {"action": action, "reason": reason, "setting": setting}

    def decide(self, sid, scenario_id, action, reason, setting=None, commit=False):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            scenario = self._current(db, sid, scenario_id)
            decision = self._decision(scenario, action, reason, setting)
            previous = db.execute("SELECT value FROM sim_events WHERE session_id = ? AND scenario_id = ? AND kind = 'revise' ORDER BY rowid DESC LIMIT 1", (sid, scenario_id)).fetchone()
            if previous is None or json.loads(previous["value"]) != decision:
                db.execute("INSERT INTO sim_events VALUES (?, ?, 'revise', ?, ?)", (sid, scenario_id, json.dumps(decision), time.time_ns() // 1_000_000))
            if not commit:
                return self._state(db, sid)
            events = [dict(e) for e in db.execute("SELECT * FROM sim_events WHERE session_id = ? AND scenario_id = ? ORDER BY timestamp, rowid", (sid, scenario_id))]
            run = db.execute("SELECT * FROM sim_runs WHERE session_id = ? AND scenario_id = ?", (sid, scenario_id)).fetchone()
            last = db.execute("SELECT MAX(timestamp) FROM sim_answers WHERE session_id = ?", (sid,)).fetchone()[0] or 0
            timestamp = max(time.time_ns() // 1_000_000, last + 1)
            rubric = score(scenario, action, reason, setting)
            db.execute("INSERT INTO sim_answers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (sid, scenario_id, scenario["skill_id"], rubric["correct"], action, reason, setting, timestamp,
                        len({e["value"] for e in events if e["kind"] == "inspect"}), sum(e["kind"] == "hint" for e in events),
                        max(0, sum(e["kind"] == "revise" for e in events) - 1), max(0, timestamp - run["started_at"]), scenario["phase"], run["prediction"]))
            result = self._state(db, sid)
            if scenario["phase"] == "practice":
                components = []
                if not rubric["action_ok"]: components.append("Revisit how your decision meets the task.")
                if not rubric["reason_ok"]: components.append("Choose reasoning supported by the inspected evidence.")
                if not rubric["setting_ok"]: components.append("The execution setting does not meet the stated constraint.")
                result["feedback"] = {**rubric, "explanation": scenario["feedback"], "coaching": components,
                                      "lesson": SKILLS[scenario["skill_id"]]["lesson"]}
            else:
                result["feedback"] = {"recorded": True}
            return result

    def delete(self, sid):
        with self.connect() as db:
            if not db.execute("SELECT id FROM sim_sessions WHERE id = ?", (sid,)).fetchone():
                raise KeyError("Session not found")
            db.execute("DELETE FROM sim_sessions WHERE id = ?", (sid,))

    def export(self, output, completed_only=False):
        with self.connect() as db:
            sessions = pd.read_sql_query("""SELECT s.id AS session_id, s.condition, s.consent,
                s.version AS bank_version, COUNT(a.scenario_id) AS answered
                FROM sim_sessions s LEFT JOIN sim_answers a ON a.session_id = s.id
                WHERE s.consent = 1 GROUP BY s.id ORDER BY s.id""", db)
            answers = pd.read_sql_query("""SELECT a.*, s.condition, s.consent, s.version AS bank_version FROM sim_answers a
                JOIN sim_sessions s ON a.session_id = s.id WHERE s.consent = 1 ORDER BY a.session_id, a.timestamp""", db)
            events = pd.read_sql_query("""SELECT e.* FROM sim_events e JOIN sim_sessions s ON e.session_id = s.id
                WHERE s.consent = 1 ORDER BY e.session_id, e.timestamp, e.rowid""", db)
        sessions["expected_total"] = sessions.bank_version.map({v: len(bank) for v, bank in BANKS.items()})
        sessions["completed"] = sessions.expected_total.notna() & sessions.answered.eq(sessions.expected_total)
        if completed_only:
            valid = sessions.loc[sessions.completed, "session_id"]
            answers = answers[answers.session_id.isin(valid)].copy()
            events = events[events.session_id.isin(valid)].copy()
        # Always retain assignment/dropout denominators, including zero-answer sessions.
        ids = sorted(sessions.session_id)
        mapping = {sid: f"learner-{i:04d}" for i, sid in enumerate(ids, 1)}
        for frame in [answers, events, sessions]:
            frame.insert(0, "student_id", frame.session_id.map(mapping))
            frame.drop(columns="session_id", inplace=True)
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        answers.to_csv(output, index=False)
        events.to_csv(output.with_name(output.stem + "_events.csv"), index=False)
        sessions.to_csv(output.with_name(output.stem + "_sessions.csv"), index=False)
        return len(answers)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="data/processed/learning/sessions.sqlite3")
    p.add_argument("--output", default="data/processed/simulator/interactions.csv")
    p.add_argument("--completed-only", action="store_true")
    a = p.parse_args()
    print(f"Exported {SimulatorService(a.db).export(a.output, a.completed_only)} opt-in decisions, companion event log, and session assignments/completion counts.")
