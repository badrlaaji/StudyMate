"""Feynman mode: the LLM judges each key idea, the code computes the score (D2)."""

from pydantic import BaseModel

from agent.llm import invoke_structured
from course.notions import Notion

MAX_ERROR_PENALTY = 2
LANGUAGES = {"en": "English", "fr": "French"}

JUDGE_PROMPT = """A student explains the notion "{name}" in their own words
(Feynman technique). Judge the explanation against the numbered key ideas only.
- ideas: for EVERY key idea, its index and covered = true if the explanation states
  it correctly (other words are fine), false otherwise.
- errors: factual mistakes in the explanation, each in one short sentence in
  {language}; [] if none. Missing ideas are not errors.
- follow_up: one short question in {language} that makes the student think about a
  missing idea (or go deeper if all are covered).

KEY IDEAS
{ideas}

STUDENT EXPLANATION
{explanation}"""


class IdeaVerdict(BaseModel):
    """Judge's verdict on one key idea."""

    index: int
    covered: bool


class Judgement(BaseModel):
    """Structured output of the Feynman judge (no score: the code computes it)."""

    ideas: list[IdeaVerdict]
    errors: list[str]
    follow_up: str


def round_half_up(value: float) -> int:
    """Round 2.5 to 3 (Python's round() gives 2: it rounds halves to even)."""
    return int(value + 0.5)


def feynman_score(covered: int, total: int, errors: int) -> int:
    """D2: clamp(round(5 x covered / total) - min(errors, 2), 0, 5)."""
    raw = round_half_up(5 * covered / total) - min(errors, MAX_ERROR_PENALTY)
    return max(0, min(5, raw))


def key_ideas(notion: Notion, lang: str) -> list[str]:
    """Key ideas of a notion in the requested language."""
    return [idea.fr if lang == "fr" else idea.en for idea in notion.key_ideas]


def judge_prompt(notion: Notion, explanation: str, lang: str) -> str:
    """Number the key ideas and add the student's explanation."""
    ideas = "\n".join(f"{i}. {text}" for i, text in enumerate(key_ideas(notion, lang)))
    name = notion.name_fr if lang == "fr" else notion.name_en
    return JUDGE_PROMPT.format(
        name=name, language=LANGUAGES[lang], ideas=ideas, explanation=explanation
    )


def grade(notion: Notion, judgement: Judgement, lang: str) -> dict:
    """Turn the verdicts into covered/missing lists and the code-computed score."""
    ideas = key_ideas(notion, lang)
    covered_ids = {
        v.index for v in judgement.ideas if v.covered and 0 <= v.index < len(ideas)
    }
    return {
        "covered": [idea for i, idea in enumerate(ideas) if i in covered_ids],
        "missing": [idea for i, idea in enumerate(ideas) if i not in covered_ids],
        "errors": judgement.errors,
        "score": feynman_score(len(covered_ids), len(ideas), len(judgement.errors)),
        "follow_up": judgement.follow_up,
        "pages": notion.pages,
    }


def evaluate_explanation(notion: Notion, explanation: str, lang: str, llm=None) -> dict:
    """Ask the judge, then grade by code."""
    prompt = judge_prompt(notion, explanation, lang)
    return grade(notion, invoke_structured(Judgement, prompt, llm=llm), lang)
