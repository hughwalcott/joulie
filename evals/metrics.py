"""Objective, model-independent metrics over a results-*.json run.

These need no human grading, so they can be compared across models directly:
whether the model ever declines, whether it obeys the kiosk's spoken-output
rules, and how it attributes claims.

    python3 evals/metrics.py evals/results-*.json
"""

import json
import re
import statistics
import sys
from pathlib import Path

# An explicit refusal: the model says the material it was given does not contain
# the answer, rather than producing one anyway.
UNCERTAIN = re.compile(
    r"don't know|do not know|not sure|no information|isn't covered|is not covered|"
    r"cannot find|couldn't find|can't find|doesn't (?:say|cover|answer)|"
    r"do not have (?:that|this|enough)|don't have (?:that|this|enough)|"
    r"material (?:doesn't|does not)|not something I|take a message|"
    r"(?:isn't|is not|aren't|are not|not) (?:explicitly )?"
    r"(?:mentioned|specified|provided|listed|detailed|available) (?:in|by|anywhere)|"
    r"(?:isn't|is not) (?:a )?specific \w+ (?:or \w+ )?mentioned|"
    r"figures aren't|number.{0,12}isn't specified|"
    r"don't have (?:specific |access to )?(?:information|details|data)|"
    r"(?:materials|sources|information) (?:provided |available |shared )?"
    r"(?:don't|doesn't|do not|does not)\s+(?:specifically )?"
    r"(?:specify|cover|address|include|explain|mention|detail|compare|provide)|"
    r"(?:don't|doesn't) see a specific|aren't (?:covered|detailed|specified|included)|"
    r"(?:isn't|is not|aren't) (?:covered|referenced) in",
    re.I,
)

# Sending the person to an authoritative source rather than answering from memory.
DEFERS = re.compile(
    r"check (?:directly )?with|check the latest|refer to the latest|consult (?:the|with|your)|"
    r"recommend checking|best to check|visit(?:ing)? the .{0,20}website|"
    r"refer to the .{0,30}(?:report|guidelines|website)",
    re.I,
)
BULLET = re.compile(r"^\s*[-*•]\s|\*\*", re.M)
SENTENCE = re.compile(r"[.!?](?:\s|$)")


def score(path: Path) -> dict:
    rows = json.loads(path.read_text())
    main = [r for r in rows if not r["id"].endswith("-rephrased")]
    n = len(main)
    # Models differ in curly vs straight apostrophes; normalise before matching.
    ans = [r["answer"].replace("\u2019", "'") for r in main]
    return {
        "model": path.stem.replace("results-", ""),
        "n": n,
        "declines": sum(bool(UNCERTAIN.search(a)) for a in ans),
        "defers_to_source": sum(bool(DEFERS.search(a)) for a in ans),
        "bullets": sum(bool(BULLET.search(a)) for a in ans),
        "over_4_sentences": sum(len(SENTENCE.findall(a)) > 4 for a in ans),
        "spoken_url": sum("http" in a for a in ans),
        "names_eeca": sum("EECA" in a for a in ans),
        "names_ea": sum(bool(re.search(r"Electricity Authority", a)) for a in ans),
        "attributes_rewiring": sum("Rewiring" in a for a in ans),
        "cites_a_year": sum(bool(re.search(r"\b20[12]\d\b", a)) for a in ans),
        "median_words": int(statistics.median(len(a.split()) for a in ans)),
        "median_s": round(statistics.median(r["seconds"] for r in main), 1),
        "max_s": round(max(r["seconds"] for r in main), 1),
        "errors": sum(bool(r.get("error")) for r in main),
    }


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]] or sorted(Path("evals").glob("results-*.json"))
    stats = [score(p) for p in paths]
    keys = [k for k in stats[0] if k != "model"]
    w = max(len(k) for k in keys) + 2
    head = "".join(f"{s['model'][:26]:>28}" for s in stats)
    print(f"{'metric':<{w}}{head}")
    for k in keys:
        print(f"{k:<{w}}" + "".join(f"{s[k]:>28}" for s in stats))


if __name__ == "__main__":
    main()
