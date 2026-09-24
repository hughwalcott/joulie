"""Paired bootstrap CI on figure recall between two runs of the question bank.

figure_recall is computed over answers the model samples at Ollama's default
temperature, so two runs of the SAME config do not agree — the baseline's own
re-run moved it by 0.027 (logs/latency-analysis.md, "The noise floor"). A
single-number comparison is therefore not readable on its own: this reports the
95% CI on the per-question difference, so a change can be separated from a
re-roll.

    python3 evals/bootstrap_recall.py evals/results-tuning-a-baseline.json \
        evals/results-tuning-a2-baseline-repeat.json evals/results-tuning-c-topk3.json

The first path is the baseline; every other is compared against it over the
questions the two have in common whose expected answer carries a checkable
figure. An interval that crosses zero means the run is inside the noise.
"""

import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.compare_runs import figure_recall, load

RESAMPLES = 4000
SEED = 20260917  # fixed so the intervals in logs/latency-analysis.md reproduce


def paired_recalls(base: dict, other: dict) -> list[tuple[str, float, float]]:
    """Per-question (id, baseline recall, other recall) for the questions both
    runs answered and whose expected answer carries a figure to check."""
    pairs = []
    for qid, row in base.items():
        if qid.endswith("-rephrased") or qid not in other:
            continue
        a = figure_recall(row["expected"], row["answer"])
        b = figure_recall(other[qid]["expected"], other[qid]["answer"])
        if a is not None and b is not None:
            pairs.append((qid, a, b))
    return pairs


def bootstrap(deltas: list[float], rng: random.Random) -> tuple[float, float]:
    n = len(deltas)
    means = sorted(
        statistics.mean(rng.choices(deltas, k=n)) for _ in range(RESAMPLES)
    )
    return means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES)]


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]]
    if len(paths) < 2:
        sys.exit(__doc__)
    base_path, base = paths[0], load(paths[0])
    rng = random.Random(SEED)

    base_pairs = paired_recalls(base, base)
    print(f"[bootstrap] baseline {base_path.stem}: "
          f"figure recall {statistics.mean(r for _, r, _ in base_pairs):.3f} "
          f"over {len(base_pairs)} questions with a checkable figure")
    print(f"\n{'run':<34}{'recall':>9}{'delta':>9}{'95% CI':>20}   verdict")
    for path in paths[1:]:
        pairs = paired_recalls(base, load(path))
        deltas = [b - a for _, a, b in pairs]
        recall = statistics.mean(b for _, _, b in pairs)
        lo, hi = bootstrap(deltas, rng)
        verdict = "inside noise" if lo <= 0 <= hi else "REAL"
        print(f"{path.stem[:33]:<34}{recall:>9.3f}{statistics.mean(deltas):>+9.3f}"
              f"{f'[{lo:+.3f}, {hi:+.3f}]':>20}   {verdict}  (n={len(pairs)})")


if __name__ == "__main__":
    main()
