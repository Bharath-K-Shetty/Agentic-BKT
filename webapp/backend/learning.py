"""Learning API. Session tokens grant access to that session only."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StrictBool, StrictFloat, StrictInt

from src.learning.service import LearningService
from src.learning.simulator import SimulatorService

router = APIRouter(prefix="/api/learning", tags=["learning"])
ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def service():
    demo_model = ROOT / "data/processed/learning/benchmark/dkt.pt"
    return LearningService(os.environ.get("HOMIE_LEARNING_DB", str(ROOT / "data/processed/learning/sessions.sqlite3")),
                           os.environ.get("HOMIE_DKT_MODEL", str(demo_model) if demo_model.exists() else None))


@lru_cache(maxsize=1)
def simulator():
    return SimulatorService(os.environ.get("HOMIE_LEARNING_DB", str(ROOT / "data/processed/learning/sessions.sqlite3")))


class StartRequest(BaseModel):
    consent: StrictBool = False


class AnswerRequest(BaseModel):
    question_id: str
    choice: StrictInt


class LessonRequest(BaseModel):
    skill_id: StrictInt


class ScenarioRequest(BaseModel):
    scenario_id: str


class InspectRequest(ScenarioRequest):
    card_id: str


class DecisionRequest(ScenarioRequest):
    action: str
    reason: StrictInt
    setting: StrictFloat | StrictInt | None = None
    commit: StrictBool = False


@router.post("/simulator/sessions")
def start_simulator(req: StartRequest):
    return simulator().start(req.consent)


@router.get("/simulator/sessions/{sid}")
def simulator_state(sid: str):
    return call(simulator().state, sid)


@router.post("/simulator/sessions/{sid}/inspect")
def inspect(sid: str, req: InspectRequest):
    return call(simulator().inspect, sid, req.scenario_id, req.card_id)


@router.post("/simulator/sessions/{sid}/hint")
def hint(sid: str, req: ScenarioRequest):
    return call(simulator().hint, sid, req.scenario_id)


@router.post("/simulator/sessions/{sid}/decision")
def decision(sid: str, req: DecisionRequest):
    return call(simulator().decide, sid, req.scenario_id, req.action, req.reason, req.setting, req.commit)


@router.delete("/simulator/sessions/{sid}")
def delete_simulator(sid: str):
    call(simulator().delete, sid)
    return {"deleted": True}


def call(method, *args):
    try:
        return method(*args)
    except KeyError as exc:
        raise HTTPException(404, "Session not found") from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/sessions")
def start(req: StartRequest):
    return service().start(req.consent)


@router.get("/sessions/{sid}")
def state(sid: str):
    return call(service().state, sid)


@router.post("/sessions/{sid}/answers")
def answer(sid: str, req: AnswerRequest):
    return call(service().answer, sid, req.question_id, req.choice)


@router.post("/sessions/{sid}/lessons")
def lesson(sid: str, req: LessonRequest):
    return call(service().lesson, sid, req.skill_id)


@router.delete("/sessions/{sid}")
def delete(sid: str):
    call(service().delete, sid)
    return {"deleted": True}
