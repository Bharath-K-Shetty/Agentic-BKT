"""Part 2 baseline: standard Deep Knowledge Tracing (Piech et al. 2015) --
an LSTM over one-hot(skill, correct) interactions, predicting per-skill
correctness at the next step. Trained/evaluated against
src.models.synthetic_quiz_data by default; swap in real HeyHomie data once
available (same student_id/skill_id/correct/timestamp schema).

Optional tag_mapping enables a mean-logit multi-tag extension: one response
remains one event, with unit input/target mass shared across its expert tags.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, roc_auc_score
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
from torch.utils.data import DataLoader, Dataset
from src.features.skill_tags import tag_indices


class DKT(nn.Module):
    def __init__(self, n_skills: int, hidden_dim: int = 64, num_layers: int = 1, n_behavior: int = 0):
        super().__init__()
        self.n_skills = n_skills
        self.n_behavior = n_behavior
        self.lstm = nn.LSTM(2 * n_skills + n_behavior, hidden_dim, num_layers=num_layers, batch_first=True)
        self.output = nn.Linear(hidden_dim, n_skills)

    def forward(self, x: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        packed = pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
        out_packed, _ = self.lstm(packed)
        out, _ = pad_packed_sequence(out_packed, batch_first=True, total_length=x.size(1))
        return self.output(out)  # (batch, seq_len, n_skills) logits


class DKTDataset(Dataset):
    def __init__(self, df: pd.DataFrame, n_skills: int, behavior_columns=(), tag_mapping=None):
        self.n_skills = n_skills
        self.behavior_columns = list(behavior_columns)
        self.tag_mapping = tag_mapping
        if tag_mapping is not None and sorted(tag_mapping.values()) != list(range(n_skills)):
            raise ValueError("Tag mapping must cover contiguous model indices")
        self.sequences: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        for _, group in df.sort_values("timestamp").groupby("student_id"):
            skills = ([tag_indices(value, tag_mapping) for value in group["tags"]]
                      if tag_mapping is not None else group["skill_id"].to_numpy())
            corrects = group["correct"].to_numpy()
            if len(skills) >= 2:
                behavior = normalize_behavior(group, self.behavior_columns)
                self.sequences.append((skills, corrects, behavior))

    def __len__(self) -> int:
        return len(self.sequences)

    def __getitem__(self, idx: int):
        skills, corrects, behavior = self.sequences[idx]
        seq_len = len(skills) - 1
        x = np.zeros((seq_len, 2 * self.n_skills + len(self.behavior_columns)), dtype=np.float32)
        if self.behavior_columns:
            x[:, 2 * self.n_skills:] = behavior[:-1]
        target_skill = np.zeros((seq_len, self.n_skills), dtype=np.float32)
        target_correct = np.zeros(seq_len, dtype=np.float32)
        for t in range(seq_len):
            if self.tag_mapping is None:
                x[t, skills[t] + self.n_skills * corrects[t]] = 1.0
                target_skill[t, skills[t + 1]] = 1.0
            else:
                # All tags share one event; targets average logits, not losses.
                current = np.asarray(skills[t], dtype=int)
                following = np.asarray(skills[t + 1], dtype=int)
                x[t, current + self.n_skills * corrects[t]] = 1.0 / len(current)
                target_skill[t, following] = 1.0 / len(following)
            target_correct[t] = corrects[t + 1]
        return (
            torch.from_numpy(x),
            torch.from_numpy(target_skill),
            torch.from_numpy(target_correct),
            seq_len,
        )


def normalize_behavior(df, columns):
    """Fixed transforms; no outcome-driven fitting or current-target features."""
    if not columns:
        return np.empty((len(df), 0), dtype=np.float32)
    scales = {"inspection_count": 3, "hint_count": 3, "revision_count": 10, "duration_ms": 600000}
    values = []
    for col in columns:
        if col not in scales:
            raise ValueError(f"Unknown behavior column: {col}")
        v = pd.to_numeric(df[col], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(v).all() or (v < 0).any():
            raise ValueError("Behavior features must be finite nonnegative values")
        values.append(np.clip(np.log1p(v) / np.log1p(scales[col]), 0, 1))
    return np.array(values, dtype=np.float32).T


def _collate(batch):
    xs, target_skills, target_corrects, lengths = zip(*batch)
    lengths = torch.tensor(lengths, dtype=torch.long)
    max_len = int(lengths.max())
    n_skills = target_skills[0].shape[1]
    batch_size = len(batch)

    x_pad = torch.zeros(batch_size, max_len, xs[0].shape[1])
    skill_pad = torch.zeros(batch_size, max_len, n_skills)
    correct_pad = torch.zeros(batch_size, max_len)
    mask = torch.zeros(batch_size, max_len)
    for i, (x, ts, tc, length) in enumerate(zip(xs, target_skills, target_corrects, lengths)):
        x_pad[i, :length] = x
        skill_pad[i, :length] = ts
        correct_pad[i, :length] = tc
        mask[i, :length] = 1.0
    return x_pad, skill_pad, correct_pad, mask, lengths


def _step_logits(model: DKT, x, skill_target, lengths):
    logits = model(x, lengths)  # (batch, seq_len, n_skills)
    return (logits * skill_target).sum(dim=-1)  # (batch, seq_len)


def train_dkt(
    df: pd.DataFrame,
    n_skills: int,
    epochs: int = 20,
    batch_size: int = 32,
    hidden_dim: int = 64,
    lr: float = 1e-3,
    seed: int = 42,
    behavior_columns=(),
    tag_mapping=None,
) -> tuple[DKT, dict]:
    torch.manual_seed(seed)
    dataset = DKTDataset(df, n_skills, behavior_columns, tag_mapping)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, collate_fn=_collate)
    model = DKT(n_skills, hidden_dim=hidden_dim, n_behavior=len(behavior_columns))
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss(reduction="none")

    history = {"loss": []}
    for _ in range(epochs):
        epoch_loss, n_steps = 0.0, 0
        for x, skill_target, correct_target, mask, lengths in loader:
            optimizer.zero_grad()
            pred_logits = _step_logits(model, x, skill_target, lengths)
            per_step_loss = loss_fn(pred_logits, correct_target) * mask
            loss = per_step_loss.sum() / mask.sum().clamp(min=1)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * mask.sum().item()
            n_steps += mask.sum().item()
        history["loss"].append(epoch_loss / max(n_steps, 1))
    return model, history


def evaluate_dkt(model: DKT, df: pd.DataFrame, n_skills: int, batch_size: int = 32, behavior_columns=(), tag_mapping=None) -> dict:
    dataset = DKTDataset(df, n_skills, behavior_columns, tag_mapping)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, collate_fn=_collate)
    model.eval()
    all_probs, all_targets = [], []
    with torch.no_grad():
        for x, skill_target, correct_target, mask, lengths in loader:
            pred_logits = _step_logits(model, x, skill_target, lengths)
            probs = torch.sigmoid(pred_logits)
            m = mask.bool()
            all_probs.append(probs[m].numpy())
            all_targets.append(correct_target[m].numpy())
    y_score = np.concatenate(all_probs) if all_probs else np.array([])
    y_true = np.concatenate(all_targets) if all_targets else np.array([])
    if len(np.unique(y_true)) < 2:
        auc = float("nan")
    else:
        auc = roc_auc_score(y_true, y_score)
    acc = accuracy_score(y_true, (y_score >= 0.5).astype(int)) if len(y_true) else float("nan")
    return {"auc": auc, "acc": acc, "n_predictions": len(y_true)}
