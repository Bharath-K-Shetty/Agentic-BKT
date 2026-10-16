"""Run against a local HOMIE server; creates and deletes one disposable demo."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.learning.scenarios import BY_ID, SCENARIOS


def main(base="http://127.0.0.1:8420/api/learning/simulator"):

    def call(path, method="GET", body=None):
        req = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                      method=method, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as response:
            return json.load(response)

    state = call("/sessions", "POST", {"consent": False})
    sid = state["session_id"]
    try:
        while state["scenario"]:
            qid = state["scenario"]["id"]
            scenario = BY_ID[qid]
            state = call(f"/sessions/{sid}/inspect", "POST", {"scenario_id": qid, "card_id": "card-0"})
            assert state["inspected"][0]["body"]
            if scenario["phase"] == "practice":
                state = call(f"/sessions/{sid}/hint", "POST", {"scenario_id": qid})
                assert state["hint"]
            else:
                try:
                    call(f"/sessions/{sid}/hint", "POST", {"scenario_id": qid})
                except HTTPError as exc:
                    assert exc.code == 409
                else:
                    raise AssertionError("Assessment hint unexpectedly allowed")
            body = {"scenario_id": qid, "action": scenario["rubric"]["action"], "reason": scenario["rubric"]["reason"],
                    "setting": scenario["setting"]["safe_max"] if scenario["setting"] else None, "commit": False}
            call(f"/sessions/{sid}/decision", "POST", body)
            state = call(f"/sessions/{sid}/decision", "POST", {**body, "commit": True})
            if scenario["phase"] != "practice":
                assert state["feedback"] == {"recorded": True}
        assert state["scores"]["transfer"] == {"correct": 5, "total": 5}
        assert len(state["review"]) == len(SCENARIOS)
        assert call(f"/sessions/{sid}")["answered"] == len(SCENARIOS)
    finally:
        call(f"/sessions/{sid}", "DELETE")
    try:
        call(f"/sessions/{sid}")
    except HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("Deleted session still exists")
    print("Verified live HTTP: diagnostic, practice and transfer decisions, evidence, drafts, hints, settings, transfer restrictions, final review, resume, and deletion.")


if __name__ == "__main__":
    main()
