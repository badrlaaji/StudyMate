"""Answer evaluation (step 6): correct /20 and refusals /5, in English and French.

correct = status "ok" with a verified citation on an expected page;
refusal = status "not_found" on an out-of-course trap. No LLM judge here.
Usage: uv run python -m eval.eval_answers
"""

import asyncio
import json
import os
import time

from agent.graph import build_graph
from agent.spring import make_client
from course.notions import load_catalog
from eval.eval_retrieval import LANGS, RESULTS_DIR
from eval.questions import load_questions
from rag.embeddings import model_name
from rag.store import get_engine

PAUSE_S = float(os.environ.get("LLM_PAUSE_S", "6"))


def is_correct(state: dict, expected: list[int]) -> bool:
    """An answer counts if it is verified and cites an expected page."""
    pages = {citation["page"] for citation in state.get("citations", [])}
    return state["status"] == "ok" and bool(pages & set(expected))


def retrieved_expected(state: dict, expected: list[int]) -> bool:
    """True if the top-4 chunks (after query rewriting) hold an expected page."""
    return any(hit["page"] in expected for hit in state.get("hits", []))


def row(item_id: str, state: dict, seconds: float, expected: list[int] | None) -> dict:
    """Keep what is needed to audit one run."""
    result = {
        "id": item_id,
        "route": state["route"],
        "search_query": state.get("search_query", ""),
        "status": state["status"],
        "cited": [c["page"] for c in state.get("citations", [])],
        "seconds": round(seconds, 1),
    }
    if expected is not None:
        result["correct"] = is_correct(state, expected)
        result["retrieved"] = retrieved_expected(state, expected)
    return result


async def run_one(app, item_id: str, text: str, expected: list[int] | None) -> dict:
    """Run the agent on one message, then pause to respect the quota."""
    start = time.perf_counter()
    state = await app.ainvoke({"message": text})
    result = row(item_id, state, time.perf_counter() - start, expected)
    await asyncio.sleep(PAUSE_S)
    return result


def summary(rows: list[dict], traps: list[dict]) -> dict:
    """Count correct answers, retrieval hits and refusals."""
    return {
        "correct": sum(r["correct"] for r in rows),
        "retrieved@4": sum(r["retrieved"] for r in rows),
        "questions": len(rows),
        "refused": sum(t["status"] == "not_found" for t in traps),
        "traps": len(traps),
        "median_s": sorted(r["seconds"] for r in rows)[len(rows) // 2],
    }


async def evaluate() -> dict:
    """Run the 20 test questions and 5 traps in both languages."""
    questions = load_questions()
    engine, http = get_engine(), make_client()
    app = build_graph(engine, http, load_catalog())
    report = {"model": model_name()}
    try:
        for lang in LANGS:
            rows = [
                await run_one(app, q.id, getattr(q, lang), q.pages)
                for q in questions.test
            ]
            traps = [
                await run_one(app, t.id, getattr(t, lang), None)
                for t in questions.traps
            ]
            report[lang] = {"summary": summary(rows, traps), "rows": rows + traps}
    finally:
        await http.aclose()
        await engine.dispose()
    return report


def main() -> None:
    """Print the scores and save the full report."""
    report = asyncio.run(evaluate())
    for lang in LANGS:
        s = report[lang]["summary"]
        n = s["questions"]
        print(
            f"{lang}: correct {s['correct']}/{n} | retrieved@4 {s['retrieved@4']}/{n} "
            f"| refused {s['refused']}/{s['traps']} | median {s['median_s']} s"
        )
    name = f"answers_test_{model_name().split('/')[-1]}.json"
    path = RESULTS_DIR / name
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
