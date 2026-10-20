"""Feynman judge agreement (step 7): code score vs blind human score, within ±1.

Usage: uv run python -m eval.eval_feynman
Blind protocol: refuses to run until every human_score is filled in feynman_set.json.
"""

import json
import os
import sys
import time

from agent.feynman import evaluate_explanation
from config import ROOT
from course.notions import load_catalog
from eval.eval_retrieval import RESULTS_DIR

SET_PATH = ROOT / "eval" / "feynman_set.json"
PAUSE_S = float(os.environ.get("LLM_PAUSE_S", "6"))
TOLERANCE = 1


def agreement(pairs: list[tuple[int, int]], tolerance: int = TOLERANCE) -> dict:
    """Share of (code, human) scores within ±tolerance, and mean absolute error."""
    n = len(pairs)
    within = sum(abs(code - human) <= tolerance for code, human in pairs)
    mae = sum(abs(code - human) for code, human in pairs) / n
    return {
        "n": n,
        "within_1": within,
        "rate": round(within / n, 3),
        "mae": round(mae, 2),
    }


def main() -> None:
    """Judge the 20 explanations and compare with the human scores."""
    items = json.loads(SET_PATH.read_text(encoding="utf-8"))["items"]
    if any(item["human_score"] is None for item in items):
        sys.exit("Blind protocol: fill every human_score (0-5) in feynman_set.json.")
    notions = {notion.id: notion for notion in load_catalog().notions}
    rows = []
    for item in items:
        notion = notions[item["notion_id"]]
        result = evaluate_explanation(notion, item["explanation"], item["lang"])
        rows.append(
            {"id": item["id"], "code": result["score"], "human": item["human_score"]}
        )
        time.sleep(PAUSE_S)
    report = agreement([(r["code"], r["human"]) for r in rows]) | {"rows": rows}
    print(f"agreement ±1: {report['within_1']}/{report['n']} | MAE {report['mae']}")
    path = RESULTS_DIR / "feynman_agreement.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
