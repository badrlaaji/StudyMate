"""RAGAS (R1): faithfulness and answer relevancy of the agent on the 20 test questions.

Usage: uv run python -m eval.eval_ragas
The judge is the same model as the generator (the only free model we use): possible
bias, stated in the README limits. ~3 LLM calls per question, cached on disk.
"""

import asyncio
import json
import os
import sys
import types

from agent.graph import build_graph
from agent.spring import make_client
from config import ROOT, get_env
from course.courses import load_registry, notions_path
from course.notions import load_catalog
from eval.eval_retrieval import RESULTS_DIR
from eval.questions import EVAL_COURSE, load_questions
from rag.embeddings import BASE_MODEL, model_name
from rag.store import get_engine

# Gemini's OpenAI-compatible endpoint: RAGAS's native Google adapter needs a sync
# client while its metrics are async; the OpenAI client works in async mode.
GEMINI_OPENAI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
RAGAS_CACHE = ROOT / ".cache" / "ragas"
PAUSE_S = float(os.environ.get("LLM_PAUSE_S", "6"))
STRICTNESS = 1  # questions generated per answer for relevancy (default 3): quota


def install_vertexai_stub() -> None:
    """ragas 0.4.3 imports a module removed from langchain-community 0.4.

    It only uses ChatVertexAI in an isinstance() list for legacy LangChain models,
    which we do not use: an empty stand-in lets ragas import, versions unchanged.
    """
    name = "langchain_community.chat_models.vertexai"
    stub = types.ModuleType(name)
    stub.ChatVertexAI = type("ChatVertexAI", (), {})
    sys.modules.setdefault(name, stub)


def ragas_metrics():
    """Build the two metrics with Gemini as judge and e5 (base) embeddings."""
    install_vertexai_stub()
    from openai import AsyncOpenAI
    from ragas.cache import DiskCacheBackend
    from ragas.embeddings import HuggingFaceEmbeddings
    from ragas.llms import llm_factory
    from ragas.metrics.collections import AnswerRelevancy, Faithfulness

    client = AsyncOpenAI(api_key=get_env("GOOGLE_API_KEY"), base_url=GEMINI_OPENAI_URL)
    cache = DiskCacheBackend(cache_dir=str(RAGAS_CACHE))
    llm = llm_factory(
        get_env("LLM_MODEL"), provider="openai", client=client, cache=cache
    )
    embeddings = HuggingFaceEmbeddings(model=BASE_MODEL)
    return Faithfulness(llm=llm), AnswerRelevancy(
        llm=llm, embeddings=embeddings, strictness=STRICTNESS
    )


def mean(values: list[float]) -> float:
    """Average rounded to 3 decimals."""
    return round(sum(values) / len(values), 3)


async def evaluate() -> dict:
    """Run the agent on the test questions (EN), then score the answered ones."""
    faithfulness, relevancy = ragas_metrics()
    engine, http = get_engine(), make_client()
    catalogs = {EVAL_COURSE: load_catalog(notions_path(EVAL_COURSE))}
    app = build_graph(engine, http, load_registry(), catalogs)
    rows = []
    try:
        for question in load_questions().test:
            message = {"message": question.en, "course": EVAL_COURSE}
            state = await app.ainvoke(message)
            if state["status"] != "ok":
                rows.append({"id": question.id, "status": state["status"]})
                continue
            contexts = [hit["text"] for hit in state["hits"]]
            f = await faithfulness.ascore(
                user_input=question.en,
                response=state["answer"],
                retrieved_contexts=contexts,
            )
            r = await relevancy.ascore(user_input=question.en, response=state["answer"])
            rows.append(
                {
                    "id": question.id,
                    "faithfulness": f.value,
                    "relevancy": round(r.value, 3),
                }
            )
            await asyncio.sleep(PAUSE_S)
    finally:
        await http.aclose()
        await engine.dispose()
    scored = [row for row in rows if "faithfulness" in row]
    return {
        "model": model_name(),
        "judge": get_env("LLM_MODEL"),
        "scored": len(scored),
        "faithfulness": mean([row["faithfulness"] for row in scored]),
        "answer_relevancy": mean([row["relevancy"] for row in scored]),
        "rows": rows,
    }


def main() -> None:
    """Print the averages and save the report."""
    report = asyncio.run(evaluate())
    print(
        f"scored {report['scored']}/20 | faithfulness {report['faithfulness']} "
        f"| answer relevancy {report['answer_relevancy']}"
    )
    path = RESULTS_DIR / f"ragas_test_{model_name().split('/')[-1]}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
