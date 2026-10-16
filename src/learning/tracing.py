"""Next-answer predictions from historical responses only."""
from __future__ import annotations

import numpy as np
import torch

from src.models.dkt import DKT


def bkt_update(mastery, correct, learn=0.15, guess=0.2, slip=0.1):
    if correct:
        posterior = mastery * (1 - slip) / (mastery * (1 - slip) + (1 - mastery) * guess)
    else:
        posterior = mastery * slip / (mastery * slip + (1 - mastery) * (1 - guess))
    return posterior + (1 - posterior) * learn


def bkt_predictions(history, n_skills, params=None):
    params = params or [(0.3, 0.15, 0.2, 0.1)] * n_skills
    states = [p[0] for p in params]
    for row in history:
        skill = int(row["skill_id"])
        _, learn, guess, slip = params[skill]
        states[skill] = bkt_update(states[skill], int(row["correct"]), learn, guess, slip)
    return np.array([states[s] * (1 - params[s][3]) + (1 - states[s]) * params[s][2]
                     for s in range(n_skills)])


def load_checkpoint(path):
    artifact = torch.load(path, map_location="cpu", weights_only=True)
    model = DKT(artifact["n_skills"], hidden_dim=artifact["hidden_dim"])
    model.load_state_dict(artifact["state_dict"])
    model.eval()
    return model, artifact


def dkt_predictions(model, history):
    if not history:
        return np.full(model.n_skills, 0.5)
    x = torch.zeros(1, len(history), 2 * model.n_skills)
    for t, row in enumerate(history):
        x[0, t, int(row["skill_id"]) + model.n_skills * int(row["correct"])] = 1
    with torch.no_grad():
        return torch.sigmoid(model(x, torch.tensor([len(history)]))[0, -1]).numpy()
