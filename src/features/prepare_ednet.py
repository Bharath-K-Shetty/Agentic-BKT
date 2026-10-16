"""Create a deterministic EdNet KT2 pilot without extracting 300K files.

One question per submitted bundle prevents within-submission answer leakage.
The seven TOEIC parts are coarse categories, not individual knowledge skills.
"""
import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from src.data_collection.fetch_ednet import sha256
from src.features.skill_tags import tag_mapping


def rank(seed, value):
    return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()


def learner_rows(events, questions, student_id, seed=42):
    """Only use final choices from explicit enter/submit bundle pairs.

    Row order resolves timestamp ties within the raw file; output timestamp is
    an ordinal, with original submission time retained separately. Duration is
    bundle wall time and does not claim to measure active time on a question.
    """
    rows, counts = [], Counter()
    active, responses, started, previous_time = None, {}, None, None
    for position, event in enumerate(events):
        time = int(event["timestamp"])
        if previous_time is not None and time < previous_time:
            raise ValueError(f"Unordered raw timestamps for {student_id}")
        previous_time = time
        action, item = event["action_type"], event["item_id"]
        if action == "enter":
            if active is not None:
                counts["abandoned_bundle"] += 1
            active, responses, started = item, {}, time
        elif action == "respond":
            meta = questions.get(item)
            answer = event["user_answer"].strip().lower()
            if active is None or meta is None or meta["bundle_id"] != active or answer not in "abcd" or len(answer) != 1:
                counts["ignored_response"] += 1
                continue
            old = responses.get(item)
            revisions = (old["revisions"] + int(old["answer"] != answer)) if old else 0
            responses[item] = {"answer": answer, "revisions": revisions, "position": position}
        elif action == "submit":
            if active != item or not responses:
                counts["unmatched_or_empty_submit"] += 1
                active, responses, started = None, {}, None
                continue
            # Choice depends only on question IDs and seed, never correctness.
            selected = min(responses, key=lambda q: rank(seed, q))
            response, meta = responses[selected], questions[selected]
            rows.append({"student_id": student_id, "timestamp": len(rows),
                         "source_timestamp_ms": time, "source_row": position,
                         "question_id": selected, "bundle_id": active,
                         "skill_id": int(meta["part"]) - 1, "part": int(meta["part"]),
                         "tags": meta["tags"], "correct": int(response["answer"] == meta["correct_answer"]),
                         "revision_count": response["revisions"], "duration_ms": time - started,
                         "platform": event.get("platform", ""), "source": event.get("source", "")})
            counts["submitted_bundles"] += 1
            counts["other_answers_excluded"] += len(responses) - 1
            active, responses, started = None, {}, None
        else:
            raise ValueError(f"Unknown KT2 action: {action}")
    if active is not None:
        counts["abandoned_bundle"] += 1
    return rows, counts


def prepare(kt2, contents, output, learners=1000, minimum=20, maximum=100, seed=42, exclude_input=None):
    if learners < 6 or minimum < 2 or maximum < minimum:
        raise ValueError("Need >=6 learners and 2 <= min responses <= max responses")
    with ZipFile(contents) as archive:
        metadata = pd.read_csv(archive.open("contents/questions.csv"), keep_default_na=False)
    if metadata.question_id.duplicated().any() or not metadata.part.isin(range(1, 8)).all():
        raise ValueError("Unexpected question metadata")
    questions = metadata.set_index("question_id").to_dict("index")
    excluded = set(pd.read_csv(exclude_input, usecols=["student_id"], dtype=str).student_id) if exclude_input else set()
    all_rows, exclusions, scanned, selected = [], Counter(), 0, []
    with ZipFile(kt2) as archive:
        members = [n for n in archive.namelist() if n.startswith("KT2/u") and n.endswith(".csv") and "/._" not in n]
        if not members:
            raise ValueError("KT2 learner CSV files not found")
        members.sort(key=lambda n: rank(seed, Path(n).stem))
        for member in members:
            student = Path(member).stem
            if student in excluded:
                exclusions["prior_cohort_files_excluded"] += 1
                continue
            with archive.open(member) as raw:
                events = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8"))
                rows, counters = learner_rows(events, questions, student, seed)
            scanned += 1
            exclusions.update(counters)
            if len(rows) < minimum:
                exclusions["learners_below_minimum"] += 1
                continue
            exclusions["responses_truncated"] += max(0, len(rows) - maximum)
            all_rows.extend(rows[:maximum])
            selected.append(student)
            if len(selected) % 100 == 0:
                print(f"Prepared {len(selected)} learners ({scanned} scanned)", flush=True)
            if len(selected) == learners:
                break
    if len(selected) != learners:
        raise ValueError(f"Only {len(selected)} eligible learners; requested {learners}")
    output.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(all_rows).sort_values(["student_id", "timestamp"], kind="stable")
    path = output / "interactions.csv"
    df.to_csv(path, index=False)
    manifest = {"dataset": "EdNet-KT2", "data_source": "public_real_learner_logs",
                "publisher": "https://github.com/riiid/ednet", "license": "CC BY-NC 4.0",
                "seed": seed, "n_skills": 7, "skill_definition": "TOEIC part minus one; coarse task category, not atomic skill",
                "skill_mapping": {str(i): f"TOEIC part {i+1}" for i in range(7)},
                "selection": "SHA256(seed:learner_id) ascending; first eligible learners; earliest responses truncated",
                "bundle_policy": "One final answer per submitted bundle, selected by SHA256(seed:question_id); other answers excluded",
                "ordering": "Submission order; timestamp is ordinal; original shifted timestamp retained as source_timestamp_ms",
                "behavior": {"revision_count": "Changed choices for selected question before bundle submission; identical repeats excluded",
                             "duration_ms": "Bundle enter-to-submit wall time; includes inactivity; not per-question active time"},
                "requested_learners": learners, "min_responses": minimum, "max_responses": maximum,
                "excluded_prior_learners": len(excluded),
                "exclude_input_sha256": sha256(exclude_input) if exclude_input else None,
                "tag_mapping": tag_mapping(metadata.tags),
                "learners": len(selected), "responses": len(df), "correct_rate": float(df.correct.mean()),
                "learners_scanned": scanned, "archive_learner_files": len(members),
                "scanned_file_counts": dict(exclusions), "part_counts": {str(k): int(v) for k,v in df.part.value_counts().items()},
                "input_sha256": {"kt2": sha256(kt2), "contents": sha256(contents)}, "output_sha256": sha256(path),
                "limitations": ["English/TOEIC data; no DeFi learning-effect evidence", "Pilot selects learners with >= minimum submissions",
                                "One question per bundle discards data", "Seven task categories simplify the original multi-tag skill structure",
                                "No hint or inspection features are inferred or fabricated"]}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ["learners", "responses", "correct_rate", "part_counts"]}, indent=2))
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, default=Path("data/raw/ednet"))
    p.add_argument("--output", type=Path, default=Path("data/processed/ednet/pilot"))
    p.add_argument("--learners", type=int, default=1000)
    p.add_argument("--min-responses", type=int, default=20)
    p.add_argument("--max-responses", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--exclude-input", type=Path, help="Exclude every learner in a previous cohort CSV")
    a = p.parse_args()
    prepare(a.raw / "EdNet-KT2.zip", a.raw / "contents.zip", a.output, a.learners, a.min_responses, a.max_responses, a.seed, a.exclude_input)


if __name__ == "__main__":
    main()
