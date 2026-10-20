"""Answer branch: grounded answer + citation check by code (D5)."""

from pydantic import BaseModel

from agent.llm import invoke_structured

TOP_K = 4
EXCERPT_CHARS = 300
LANGUAGES = {"en": "English", "fr": "French"}
NOT_FOUND = {
    "en": "I could not find the answer in chapters 6 and 7 of the book.",
    "fr": "Je n'ai pas trouvé la réponse dans les chapitres 6 et 7 du livre.",
}

ANSWER_PROMPT = """You are a study assistant for the textbook "Principles of Data
Science" (OpenStax). Answer the student's question using ONLY the excerpts below.
Each excerpt starts with its PDF page number as [page N].
- found: true only if the excerpts explain the answer. If false: answer "" and
  cited_pages []. Never write that the text does not mention something.
- Write the answer in {language}, in 2 to 6 sentences.
- cited_pages: the page numbers of the excerpts you actually used.
{reminder}
EXCERPTS
{excerpts}

QUESTION
{question}"""
RETRY_REMINDER = (
    "Your previous answer was rejected: its cited pages were missing or not among "
    "the excerpts. Cite only pages shown as [page N] below, or return an empty answer."
)


class AnswerDraft(BaseModel):
    """Answer proposed by the LLM, checked by code before being shown."""

    found: bool
    answer: str
    cited_pages: list[int]


def format_excerpts(hits: list[dict]) -> str:
    """Show each retrieved chunk with its [page N] marker."""
    return "\n\n".join(f"[page {hit['page']}]\n{hit['text']}" for hit in hits)


def answer_prompt(question: str, lang: str, hits: list[dict], retry: bool) -> str:
    """Fill the answer prompt (with a reminder on the second attempt)."""
    return ANSWER_PROMPT.format(
        language=LANGUAGES[lang],
        reminder=RETRY_REMINDER if retry else "",
        excerpts=format_excerpts(hits),
        question=question,
    )


def verify_citations(draft: AnswerDraft, hits: list[dict]) -> bool:
    """D5: a found, non-empty answer citing at least one page, all retrieved."""
    retrieved = {hit["page"] for hit in hits}
    cited = set(draft.cited_pages)
    has_answer = draft.found and bool(draft.answer.strip())
    return has_answer and bool(cited) and cited <= retrieved


def build_citations(pages: list[int], hits: list[dict]) -> list[dict]:
    """Return one {page, excerpt} per cited page, from the first chunk of that page."""
    citations = []
    for page in sorted(set(pages)):
        text = next(hit["text"] for hit in hits if hit["page"] == page)
        citations.append({"page": page, "excerpt": text[:EXCERPT_CHARS]})
    return citations


def generate(question: str, lang: str, hits: list[dict], retry: bool, llm=None):
    """Ask the LLM for a grounded answer."""
    prompt = answer_prompt(question, lang, hits, retry)
    return invoke_structured(AnswerDraft, prompt, llm=llm)
