"""Retrieval evaluation without LLM (D4): hit@4 and MRR@10, English vs French.

Usage: uv run python -m eval.eval_retrieval dev|test [SETTING]  (SETTING: see SETTINGS)
"""

import asyncio
import json
import sys

from sqlalchemy.ext.asyncio import AsyncEngine

from config import ROOT
from eval.questions import EvalQuestion, load_questions
from rag.embeddings import embed_query, load_model, model_name
from rag.store import get_engine, search

HIT_K = 4
MRR_K = 10
LANGS = ("en", "fr")
# End-of-chapter pages: exercises and references, not explanations (S1-3).
END_MATTER = (
    "Group Project",
    "Chapter Review",
    "Critical Thinking",
    "Quantitative Problems",
    "References",
)
RESULTS_DIR = ROOT / "eval" / "results"
# all-pages = reference; no-end-matter = skip END_MATTER sections;
# no-query-prefix = ablation: question embedded without "query: ".
SETTINGS = ("all-pages", "no-end-matter", "no-query-prefix")


def first_relevant_rank(retrieved_pages: list[int], expected: list[int]) -> int | None:
    """Return the 1-based rank of the first retrieved chunk on an expected page."""
    for rank, page in enumerate(retrieved_pages, start=1):
        if page in expected:
            return rank
    return None


def hit_at(rank: int | None, k: int = HIT_K) -> float:
    """Return 1.0 if a relevant chunk is within the top k, else 0.0."""
    return 1.0 if rank is not None and rank <= k else 0.0


def reciprocal_rank(rank: int | None, k: int = MRR_K) -> float:
    """Return 1/rank if within the top k, else 0.0."""
    return 1.0 / rank if rank is not None and rank <= k else 0.0


def summarize(ranks: list[int | None]) -> dict:
    """Return hit@4 and MRR@10 averaged over the questions."""
    n = len(ranks)
    return {
        "n": n,
        "hit@4": round(sum(hit_at(r) for r in ranks) / n, 3),
        "mrr@10": round(sum(reciprocal_rank(r) for r in ranks) / n, 3),
    }


def query_vector(text: str, model, setting: str) -> list[float]:
    """Embed a question ("query: " prefix, except in the ablation setting)."""
    if setting == "no-query-prefix":
        return model.encode([text], normalize_embeddings=True)[0].tolist()
    return embed_query(text, model)


async def top_hits(
    engine: AsyncEngine, text: str, model, setting: str, k: int
) -> list[dict]:
    """Search one text with the given setting."""
    excluded = END_MATTER if setting == "no-end-matter" else ()
    vector = query_vector(text, model, setting)
    return await search(engine, vector, model_name(), k, excluded)


async def question_rank(
    engine: AsyncEngine, question: EvalQuestion, lang: str, model, setting: str
) -> int | None:
    """Search one question in one language and return the first relevant rank."""
    hits = await top_hits(engine, getattr(question, lang), model, setting, MRR_K)
    return first_relevant_rank([hit["page"] for hit in hits], question.pages)


async def top1_scores(engine: AsyncEngine, texts: list[str], model, setting) -> list:
    """Return the best cosine score for each text."""
    scores = []
    for text in texts:
        hits = await top_hits(engine, text, model, setting, 1)
        scores.append(round(hits[0]["score"], 4))
    return scores


async def evaluate(split: str, setting: str) -> dict:
    """Evaluate one split in both languages, plus the trap score analysis."""
    questions = load_questions()
    items = getattr(questions, split)
    model = load_model(model_name())
    engine = get_engine()
    try:
        report = {"split": split, "model": model_name(), "setting": setting}
        for lang in LANGS:
            ranks = [
                await question_rank(engine, q, lang, model, setting) for q in items
            ]
            report[lang] = summarize(ranks) | {
                "ranks": dict(zip([q.id for q in items], ranks, strict=True))
            }
        in_course = [getattr(q, lang) for q in items for lang in LANGS]
        traps = [getattr(t, lang) for t in questions.traps for lang in LANGS]
        report["top1_in_course"] = await top1_scores(engine, in_course, model, setting)
        report["top1_traps"] = await top1_scores(engine, traps, model, setting)
        return report
    finally:
        await engine.dispose()


def print_report(report: dict) -> None:
    """Print the metrics table and the trap score ranges."""
    print(
        f"split={report['split']} model={report['model']} setting={report['setting']}"
    )
    print("lang  n   hit@4  MRR@10")
    for lang in LANGS:
        row = report[lang]
        print(f"{lang:4s}  {row['n']:<3d} {row['hit@4']:.3f}  {row['mrr@10']:.3f}")
    gap = report["en"]["mrr@10"] - report["fr"]["mrr@10"]
    print(f"EN - FR gap (MRR@10): {gap:+.3f}")
    inside, traps = report["top1_in_course"], report["top1_traps"]
    print(f"top-1 score in course: {min(inside):.4f}-{max(inside):.4f}")
    print(f"top-1 score traps:     {min(traps):.4f}-{max(traps):.4f}")


def main(args: list[str]) -> None:
    """Run the evaluation and save the report as JSON."""
    split = args[0] if args else "dev"
    setting = args[1] if len(args) > 1 else "all-pages"
    if split not in ("dev", "test") or setting not in SETTINGS:
        raise SystemExit(__doc__)
    report = asyncio.run(evaluate(split, setting))
    print_report(report)
    RESULTS_DIR.mkdir(exist_ok=True)
    name = f"retrieval_{split}_{setting}_{model_name().split('/')[-1]}.json"
    (RESULTS_DIR / name).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
