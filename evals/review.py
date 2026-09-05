"""Print a run's answers alongside the expected answer and the baseline verdict,
so a second model can be graded against the same rubric without drifting.

    python3 evals/review.py evals/results-<model>.json 0 20
"""

import json
import sys
from pathlib import Path

EVALS = Path(__file__).parent
BASELINE_GRADES = EVALS / "grades-llama3-2-3b-instruct-q4-k-m.json"


def main() -> None:
    path = Path(sys.argv[1])
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    stop = int(sys.argv[3]) if len(sys.argv) > 3 else start + 20

    rows = json.loads(path.read_text())
    base = json.loads(BASELINE_GRADES.read_text()) if BASELINE_GRADES.exists() else {}

    for r in rows[start:stop]:
        prior = base.get(r["id"], ["-", ""])[0]
        flag = " [VERIFIER]" if r.get("verifier") else ""
        print("=" * 78)
        print(f"{r['id']}  (3B baseline: {prior}){flag}  {r['seconds']}s")
        print(f"Q   {r['question']}")
        print(f"EXP {r['expected']}")
        print(f"GOT {r['answer']}")
        print(f"SRC {[c['publisher'] for c in r['retrieved']] or 'NONE'}")


if __name__ == "__main__":
    main()
