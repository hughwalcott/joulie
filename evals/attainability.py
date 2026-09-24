"""Estimate whether each expected answer is even reachable from the corpus.

For every distinctive figure in an expected answer (dollar amounts, percentages,
years, quantities), check whether that figure appears anywhere in the knowledge
base. A question whose key figures are entirely absent cannot be answered
correctly by any model at any size — that is a corpus gap, not a model failure,
and it sets a ceiling on what this eval can measure.

    python3 evals/attainability.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
EVALS = ROOT / "evals"

# Distinctive figures: money, percentages, and multi-digit quantities. Bare small
# integers are too common in prose to carry signal.
FIGURE = re.compile(
    r"\$[\d,]+(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?%|\b\d{4}\b|\b\d+(?:\.\d+)?\s?(?:TWh|PJ|MWh|GWh|TJ|kW|km|kg|MW)\b",
    re.I,
)


def normalise(text: str) -> str:
    return re.sub(r"[,\s]", "", text.lower())


def main() -> None:
    corpus = normalise(
        "\n".join(p.read_text(errors="ignore") for p in ROOT.glob("knowledge_base/**/*.md"))
    )

    questions = []
    for name in ("questions_1_5.json", "questions_6_12.json"):
        questions.extend(json.loads((EVALS / name).read_text()))

    rows = []
    for q in questions:
        figures = {f for f in FIGURE.findall(q["expected"])}
        # Years alone are weak evidence; ignore them if the answer has other figures.
        strong = {f for f in figures if not re.fullmatch(r"\d{4}", f)}
        check = strong or figures
        found = {f for f in check if normalise(f) in corpus}
        rows.append((q["id"], q["topic"], len(check), len(found)))

    print(f"{'id':8s} {'figures':>8s} {'in corpus':>10s}  topic")
    unattainable, partial, no_figures = [], [], []
    for qid, topic, n, hit in rows:
        if n == 0:
            no_figures.append(qid)
            continue
        if hit == 0:
            unattainable.append(qid)
        elif hit < n:
            partial.append(qid)
        print(f"{qid:8s} {n:8d} {hit:10d}  {topic}")

    print()
    print(f"questions with checkable figures : {len(rows) - len(no_figures)}")
    print(f"  none of those figures in corpus: {len(unattainable)}")
    print(f"  some figures in corpus         : {len(partial)}")
    print(f"questions with no hard figures   : {len(no_figures)} (graded on substance, not numbers)")
    print()
    print("UNATTAINABLE (no expected figure exists anywhere in the corpus):")
    print("  " + " ".join(unattainable))


if __name__ == "__main__":
    main()
