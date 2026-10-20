# StudyMate

> **Work in progress.** Steps 0-2 done (environment, book → clean pages, catalogue of 21 notions). No results yet.

A study assistant for one textbook. It answers questions with **cited and verified pages**,
routes each request (answer, quiz, revision plan), checks your understanding with a
**Feynman mode**, and tracks a **mastery map** of the course notions. English and French.

## Problem

Asking a general chatbot about a course gives fluent answers with no way to check them
against the textbook. Students need answers grounded in *their* book, with page numbers
they can open, and feedback on what they have actually understood.

## Plan

| Step | Goal |
| --- | --- |
| 0 | Repository and environment |
| 1 | Book → clean pages (chapters 6 and 7) |
| 2 | Catalogue of course notions (EN/FR) |
| 3 | Indexing: chunks + multilingual embeddings in PostgreSQL/pgvector |
| 4 | Retrieval evaluation (hit@4, MRR, EN vs FR) |
| 5 | Embedding fine-tuning and comparison |
| 6 | LangGraph agent: router, cited answers, citation check |
| 7 | FastAPI service, RAGAS, Feynman judge |
| 8 | "Study Desk" web interface (chat + PDF viewer) |
| 9 | Spring Boot mastery service, quiz, revision plan |
| 10 | CI, Docker, measurements, v1.0 |

## Stack

- **Python 3.13** (uv): FastAPI, LangGraph, LangChain, sentence-transformers, PyTorch (CPU), pypdf
- **LLM**: Google Gemini (`gemini-3.5-flash-lite`), structured outputs validated with Pydantic
- **Embeddings**: `intfloat/multilingual-e5-small`
- **Database**: PostgreSQL + pgvector (Neon in development), asyncpg
- **Front end**: Next.js 16, React 19, react-pdf, Recharts
- **Mastery service**: Spring Boot 4.1, Java 21
- **CI**: GitHub Actions, Docker Compose

## Setup (Windows, PowerShell)

```powershell
uv venv --python 3.13
.\.venv\Scripts\Activate.ps1
uv pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env   # then fill in the keys
uv run python -m scripts.check_env all
```

## Attribution

Course content: *Principles of Data Science*, OpenStax, licensed under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The book PDF is downloaded locally and never stored in this repository.

## License

Code: [MIT](LICENSE).
