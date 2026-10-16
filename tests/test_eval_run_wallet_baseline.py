import pandas as pd

from src.eval import run_wallet_baseline


def test_main_handles_single_class_train_split_without_crashing(monkeypatch, capsys):
    X = pd.DataFrame(
        {"f1": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]},
        index=[f"w{i}" for i in range(6)],
    )
    y = pd.Series([0, 0, 0, 0, 0, 0], index=X.index)  # single class, as happens at low N

    monkeypatch.setattr(run_wallet_baseline, "build_dataset", lambda raw_dir, frac: (X, y))
    monkeypatch.setattr("sys.argv", ["run_wallet_baseline"])

    run_wallet_baseline.main()  # should not raise
    out = capsys.readouterr().out
    assert "single class" in out
