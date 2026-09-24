"""Diff two results-*.json runs of the same question bank.

Grading in evals/grades-*.json is manual, so it cannot be reused when the
answers change. These proxies are objective and need no human pass: how many of
the expected answer's distinctive figures survive into the answer (the same
FIGURE test attainability.py uses against the corpus), whether the model
declined, and the kiosk's spoken-format rules. They do not replace grading —
they say whether a prompt-shape change moved answer quality enough to warrant
re-grading, and which questions to look at first.

    python3 evals/compare_runs.py evals/results-a.json evals/results-b.json
"""

import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.attainability import FIGURE, normalise
from evals.metrics import BULLET, SENTENCE, UNCERTAIN


def figure_recall(expected: str, answer: str) -> float | None:
    """Share of the expected answer's distinctive figures that appear in the
    answer. None when the expected answer carries no figure to check."""
    figures = {f for f in FIGURE.findall(expected)}
    strong = {f for f in figures if not re.fullmatch(r"\d{4}", f)}
    check = strong or figures
    if not check:
        return None
    hay = normalise(answer)
    return sum(normalise(f) in hay for f in check) / len(check)


def load(path: Path) -> dict[str, dict]:
    return {r["id"]: r for r in json.loads(path.read_text())}


def summarise(rows: dict[str, dict], ids: list[str]) -> dict:
    answers = [rows[i]["answer"].replace("’", "'") for i in ids]
    recalls = [r for r in (figure_recall(rows[i]["expected"], rows[i]["answer"]) for i in ids)
               if r is not None]
    return {
        "figure_recall": round(statistics.mean(recalls), 3) if recalls else 0.0,
        "declines": sum(bool(UNCERTAIN.search(a)) for a in answers),
        "bullets": sum(bool(BULLET.search(a)) for a in answers),
        "over_4_sentences": sum(len(SENTENCE.findall(a)) > 4 for a in answers),
        "spoken_url": sum("http" in a for a in answers),
        "attributes_rewiring": sum("Rewiring" in a for a in answers),
        "cites_a_year": sum(bool(re.search(r"\b20[12]\d\b", a)) for a in answers),
        "median_words": int(statistics.median(len(a.split()) for a in answers)),
        "median_s": round(statistics.median(rows[i]["seconds"] for i in ids), 1),
        "errors": sum(bool(rows[i].get("error")) for i in ids),
    }


def main() -> None:
    before_path, after_path = Path(sys.argv[1]), Path(sys.argv[2])
    before, after = load(before_path), load(after_path)
    ids = [i for i in before if i in after and not i.endswith("-rephrased")]
    print(f"[compare] {len(ids)} questions in both runs")
    if len(before) != len(after):
        print(f"[compare] WARNING: {len(before)} vs {len(after)} rows — comparing the overlap")

    a, b = summarise(before, ids), summarise(after, ids)
    w = max(len(k) for k in a) + 2
    print(f"\n{'metric':<{w}}{before_path.stem[:26]:>28}{after_path.stem[:26]:>28}")
    for k in a:
        print(f"{k:<{w}}{a[k]:>28}{b[k]:>28}")

    moved = []
    for i in ids:
        r_before = figure_recall(before[i]["expected"], before[i]["answer"])
        r_after = figure_recall(after[i]["expected"], after[i]["answer"])
        if r_before is not None and r_after is not None and r_before != r_after:
            moved.append((r_after - r_before, i, r_before, r_after))
    moved.sort()
    if moved:
        print(f"\n[compare] {len(moved)} questions changed figure recall — re-grade these first")
        for delta, qid, r_before, r_after in moved:
            print(f"  {qid:12s} {r_before:.2f} -> {r_after:.2f}  ({delta:+.2f})")

    # Retrieval is unchanged by prompt shape; if it differs, the runs aren't comparable.
    drifted = [i for i in ids
               if [c["title"] for c in before[i]["retrieved"]] != [c["title"] for c in after[i]["retrieved"]]]
    if drifted:
        print(f"\n[compare] WARNING: retrieval differed on {len(drifted)} questions: {drifted[:8]}")


if __name__ == "__main__":
    main()
