"""Synthetic quiz-interaction generator for the Part 2 DKT case study, since
real HeyHomie quiz/lesson data isn't available in this repo. The 4-column
schema (student_id, skill_id, correct, timestamp) is the swappable contract:
real HeyHomie data just needs to match it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def generate_synthetic_interactions(
    n_students: int = 200,
    n_skills: int = 5,
    interactions_per_student: int = 50,
    seed: int = 42,
) -> pd.DataFrame:
    """Each student has a latent per-skill mastery that grows with practice
    (a simple logistic learning-curve generator), so DKT has a real
    learnable signal rather than pure noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for student_id in range(n_students):
        practice_count = np.zeros(n_skills)
        base_ability = rng.normal(0, 1)
        skill_difficulty = rng.normal(0, 1, size=n_skills)
        for t in range(interactions_per_student):
            skill_id = int(rng.integers(0, n_skills))
            mastery = base_ability - skill_difficulty[skill_id] + 0.3 * practice_count[skill_id]
            p_correct = 1 / (1 + np.exp(-mastery))
            correct = int(rng.random() < p_correct)
            practice_count[skill_id] += 1
            rows.append(
                {
                    "student_id": student_id,
                    "skill_id": skill_id,
                    "correct": correct,
                    "timestamp": t,
                }
            )
    return pd.DataFrame(rows)
