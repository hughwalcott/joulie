"""Compare graded runs across models.

    python3 evals/compare.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

EVALS = Path(__file__).parent
SCORE = {"pass": 1.0, "partial": 0.5, "fail": 0.0}


def load(slug: str) -> tuple[dict, dict]:
    grades = {
        k: v[0]
        for k, v in json.loads((EVALS / f"grades-{slug}.json").read_text()).items()
        if not k.startswith("_")
    }
    results = {r["id"]: r for r in json.loads((EVALS / f"results-{slug}.json").read_text())}
    return grades, results


def band(grades: dict, ids: list[str]) -> str:
    c = Counter(grades[i] for i in ids)
    n = sum(c.values()) or 1
    return f'{c["pass"]:3d}{c["partial"]:5d}{c["fail"]:5d}{(c["pass"] + 0.5 * c["partial"]) / n:8.0%}'


def main() -> None:
    # Baseline first, then any other graded run found on disk.
    order_hint = ["llama3-2-3b", "qwen2-5-14b", "qwen3-14b"]
    slugs = sorted(
        (p.stem.replace("grades-", "") for p in EVALS.glob("grades-*.json")),
        key=lambda s: next((i for i, h in enumerate(order_hint) if s.startswith(h)), 99),
    )
    short = {
        "llama3-2-3b-instruct-q4-k-m": "llama3.2:3b",
        "qwen2-5-14b-instruct-q4-k-m": "qwen2.5:14b",
        "qwen3-14b-q4-k-m": "qwen3:14b",
    }
    loaded = [(short.get(s, s[:22]), *load(s)) for s in slugs]

    topics = defaultdict(list)
    _, _, ref = loaded[0]
    for qid, r in ref.items():
        if not qid.endswith("-rephrased"):
            topics[r["topic"]].append(qid)
    order = sorted(topics, key=lambda t: int(t.split(".")[0]))

    header = "".join(f"{name:>26}" for name, _, _ in loaded)
    print(f"{'':34}{header}")
    print(f"{'topic':34}" + "".join(f"{'pass part fail   score':>26}" for _ in loaded))
    for t in order:
        row = "".join(band(g, topics[t]) for _, g, _ in loaded)
        print(f"{t[:33]:34}{row}")

    allids = [q for ids in topics.values() for q in ids]
    print(f"\n{'ALL 107':34}" + "".join(band(g, allids) for _, g, _ in loaded))
    for label, pick in [
        ("Topics 1-5 policy/cost", lambda t: int(t.split(".")[0]) <= 5),
        ("Topics 6-12 technology", lambda t: int(t.split(".")[0]) >= 6),
    ]:
        ids = [q for t in order if pick(t) for q in topics[t]]
        print(f"{label:34}" + "".join(band(g, ids) for _, g, _ in loaded))
    flagged = [q for q in allids if ref[q]["verifier"]]
    print(f"{'Verifier-flagged (18)':34}" + "".join(band(g, flagged) for _, g, _ in loaded))

    base_name, base_g = loaded[0][0], loaded[0][1]
    for name, g, _ in loaded[1:]:
        better = sum(SCORE[g[q]] > SCORE[base_g[q]] for q in allids)
        worse = sum(SCORE[g[q]] < SCORE[base_g[q]] for q in allids)
        print(f"\nMovement, {base_name} -> {name}")
        print(f"  improved {better}   regressed {worse}   unchanged {len(allids) - better - worse}")
        regs = [q for q in allids if SCORE[g[q]] < SCORE[base_g[q]]]
        print("  regressions: " + (", ".join(regs) if regs else "none"))


if __name__ == "__main__":
    main()
