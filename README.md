# StudyMate

[![CI](https://github.com/badrlaaji/studymate/actions/workflows/ci.yml/badge.svg)](https://github.com/badrlaaji/studymate/actions/workflows/ci.yml)

A study assistant for **open textbooks**. Ask a question in **English or French**: the answer
cites the book's pages, the **code checks every citation**, and the cited page opens next to
the chat with the passage highlighted. Then explain a notion in your own words (**Feynman
mode**), take a **quiz** on your weak spots, and follow your **progress** notion by notion.

It ships with two courses — *Principles of Data Science* (chapters 6-7, machine learning and
deep learning; the fully evaluated reference course) and *Introductory Statistics 2e*
(chapter 12, regression and correlation) — and **a new course is added with one command**.

> Demo video (2 min): coming soon. A **public demo without any AI call** can be hosted from
> this repository: see [Public demo](#public-demo-no-ai-call).

![Ask the book: a verified answer, page 327 opened with the cited passage highlighted](docs/img/study-desk.png)

## The problem

A general chatbot gives fluent answers about a course with no way to check them against the
textbook. A student needs answers grounded in *their* book, with pages they can open, and
honest feedback on what they have actually understood.

## What it does

- **Ask the book** (`/study`): a LangGraph agent routes the message (answer, quiz or revision
  plan), retrieves passages, Gemini writes the answer, and the code accepts it only if every
  cited page was really retrieved; otherwise one retry, then "not in this course".
- **Feynman mode** (`/feynman`): explain a notion; the LLM judges each key idea of the
  catalogue, and the **code** computes the 0-5 score.
- **Progress** (`/`): mastery of every notion (average of the last 3 scores), what to review
  next with the pages to re-read, computed without any LLM.
- **Quiz** (`/quiz`): multiple-choice questions on the weakest notions (keys 1-4, Enter),
  graded by code, with the source page of each answer.
- **Library** (`/library`): one card per course (PDF, indexed passages, notions); **upload
  a textbook PDF** and choose its chapters; switch course from the sidebar. Each course has
  its own index, notions and scores.
- **Bilingual**: French questions are rewritten into a search query in the book's language;
  the interface switches between English and French. Light and dark themes.

![Progress: share of notions mastered, notions to review first, average per practised notion](docs/img/mastery-map.png)

## Public demo (no AI call)

The web app has a read-only **demo mode** (`DEMO_MODE=1`) meant for public hosting:

- The answers to a few example questions, three quizzes per language and the Feynman grades of
  example explanations were computed **once** by the real pipeline
  (`uv run python -m scripts.build_demo`) and saved in `frontend/demo/data.json`.
- Next.js answers every `/api/*` route itself: no FastAPI, no database, **no Gemini call and no
  key**. A Vitest test traps `fetch` and every socket: it fails if a demo route opens any
  outgoing connection.
- Feynman and quiz scores stay in a cookie of the visitor's browser; the progress map and the
  revision plan use the same rules as Spring (average of the last 3 scores).
- Any other question gets "example questions only"; a cited page opens on openstax.org.

Run it locally (PowerShell): `cd frontend; npm ci; npm run build; $env:DEMO_MODE="1"; npm run start`,
or with Docker: `docker build -t studymate-web frontend` then
`docker run -e DEMO_MODE=1 -p 3000:3000 studymate-web`.

Host it, for example on Vercel (Hobby plan, personal non-commercial use): import the GitHub
repository, set the root directory to `frontend`, add the environment variable `DEMO_MODE=1`,
deploy. Nothing else is needed: no secret, no database. Live link: [X] (not deployed yet).

## Add your own course

Any textbook you are allowed to reuse works (for example an [OpenStax](https://openstax.org)
book). Its text is sent to Gemini to draft the notions, so never add private documents.

**From the interface** (`/library` → *Upload a textbook*): drop the PDF (up to 100 MB),
pick chapters found in its outline or a page range (at most 150 pages), give the license and
the authors, and confirm you may use the document. The API indexes the pages, then drafts
the notions in the background; the card shows each step, a *Retry* button if Gemini's free
quota runs out, and *Delete*. Uploaded courses stay in `data/` (never in Git).

![Upload a textbook: chapters found in the PDF outline, license, authors](docs/img/upload.png)

Measured with *Introduction to Python Programming* (OpenStax, 397 pages, 15 chapters found):
chapter 5 gave 22 pages, 33 indexed passages and 5 notions; the question "What is the
difference between a for loop and a while loop?" was answered with verified citations
(pages 125 and 143).

**From the command line** (courses kept in Git): describe the course in
[`course/courses.json`](course/courses.json) (id, title, PDF link, license, chapters or a
page range), then run `uv run python -m course.add <id>`; review `course/notions/<id>.json`
and set `"validated": true`.

Measured for *Introductory Statistics 2e*, chapter 12: 61 pages, 135 indexed passages and
11 drafted notions in 3 minutes (CPU, Gemini free tier). The same question about random
forests finds page 327 in the data science course and is refused in the statistics course.

## Architecture

```mermaid
flowchart LR
  B[Browser] --> N["Next.js :3000<br/>pages + /api proxy"]
  N --> F["FastAPI :8000<br/>LangGraph agent"]
  F --> P[("PostgreSQL + pgvector<br/>chunks per course")]
  F --> G["Gemini 3.5 Flash-Lite"]
  F --> S["Spring Boot :8080<br/>scores per course"]
  S --> A[("PostgreSQL<br/>schema app")]
```

- Offline, per course: PDF → clean pages (`pypdf`, headers and footers removed) → chunks of
  at most 300 tokens → `multilingual-e5-small` embeddings (fine-tuned) → pgvector, tagged
  with the course id.
- The browser only talks to Next.js; FastAPI is the only client of Spring. If Spring is down,
  the assistant still answers and scores are simply not recorded (degraded mode).

## Results

All numbers come from the scripts in `eval/` (reports in `eval/results/`), on the reference
course *Principles of Data Science*.

**Retrieval** — 20 test questions, each asked in English and in French, written by paraphrasing
the book (not generated by the LLM). A hit is a retrieved chunk on an expected PDF page.

| Embeddings | Language | hit@4 | MRR@10 |
| --- | --- | --- | --- |
| e5-small (base) | English | 0.850 | 0.703 |
| e5-small (base) | French | 0.750 | 0.604 |
| e5-small fine-tuned | English | 0.950 | 0.722 |
| e5-small fine-tuned | French | 0.800 | 0.611 |

Fine-tuning: 560 synthetic question-passage pairs (English + French, generated by Gemini,
decontaminated against the evaluation questions), `MultipleNegativesRankingLoss`, 2 epochs on
CPU (7 min). hit@4 improves (+2 English, +1 French questions); MRR barely moves.

**Answers** — the full agent on the same 20 test questions and 5 out-of-course traps. *Correct* =
the answer passed the citation check **and** cites an expected page (no LLM judge).

| Language | Correct | Expected page in top 4 | Traps refused |
| --- | --- | --- | --- |
| English | 18/20 (19/20 before the multi-course prompts) | 18/20 | 5/5 |
| French | 19/20 | 19/20 | 5/5 |

French questions are rewritten into English search queries inside the router call (no extra
LLM call): French top-4 retrieval went from 16/20 to 19/20. The English miss (test02) came
from the same rewrite applied to an English question, which dropped words; questions in the
book's language are now searched verbatim, and test02 then cites the expected page (checked
on that question; a full re-run is pending because the free-tier quota was exhausted).

**Answer quality** (RAGAS 0.4.3, 20 English test questions, before the multi-course prompts):
faithfulness **0.934**, answer relevancy **0.931**.

**Speed** — median `/chat` latency **2.73 s** (p90 3.17 s) on 20 questions never asked before (dev set, English and French), Gemini free tier, CPU only, measured before the multi-course change (same pipeline). When the free-tier quota is saturated, the code waits 60 s and retries: one call then took 2 min 30 s.

**Front end** — Lighthouse 13.5 on the production build, and axe-core (WCAG 2.2 AA rules):
**0 violations** on the 6 pages × light/dark × desktop/mobile, and on the answered, Feynman
and quiz states.

| Page | Mobile: perf. / a11y / best pr. / SEO | Desktop |
| --- | --- | --- |
| `/` progress | 94 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/study` | 97 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/feynman` | 97 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/quiz` | 100 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |
| `/library` | 97 / 100 / 100 / 100 | 100 / 100 / 100 / 100 |

## Interface

A dot-grid notebook with one violet "highlighter" accent. Local fonts only (Bricolage
Grotesque for the interface, Literata for the book's text, both SIL OFL), inline SVG icons,
CSS tokens for light and dark themes. Mastery levels always pair colour with an icon and a
label; their colours were checked with a palette validator for colour-blind separation and
contrast. The progress chart uses one hue with threshold lines at 3 (review) and 4 (mastered).

![Feynman mode: key ideas covered or missing, score computed by code, follow-up question](docs/img/feynman.png)

![Library: one card per course, an uploaded course ready to study, the upload area](docs/img/library.png)

| Dark theme | Phone |
| --- | --- |
| ![Progress page in the dark theme](docs/img/mastery-map-dark.png) | ![Progress page on a phone](docs/img/mobile.png) |

## Limits

- **Small evaluation sets** (20 test questions, 5 traps, reference course only): differences
  of one or two questions are within noise; the fine-tuning gain is indicative only.
- **Same model as judge and generator** for RAGAS and the Feynman judge: scores may be
  optimistic. The Feynman judge is checked against blind human grades (protocol in
  `eval/eval_feynman.py`).
- **Notions of a new course are an LLM draft**: they must be reviewed by hand (the statistics
  catalogue still is a draft; its lab sections gave weak notions).
- **Formulas are lost**: they are drawn as vector graphics in the PDF, so they are absent from
  the extracted text; the PDF panel still shows them.
- **A verified citation is not always the best page**: the check proves the page was retrieved
  and cited, not that it is the most relevant one.
- **Free tier**: rate limits and occasional 503 errors from Gemini; the code waits and retries
  once. The full app is not deployed publicly (the free tier does not allow it for EU/UK users):
  only the demo mode, which never calls Gemini, is meant to be public.
- **The public demo is frozen**: it only answers its example questions and grades its example
  explanations; scores live in one browser and are lost with its cookies.

## Run it

Windows, PowerShell, Python 3.13 with [uv](https://docs.astral.sh/uv/), Node 22, JDK 21:

```powershell
uv venv --python 3.13
uv pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env              # Gemini key, Neon connection strings
uv run python -m scripts.check_env all
uv run python -m course.add data-science # download + index (its notions are in the repo)
uv run python -m course.add statistics
.\scripts\dev.ps1                        # API :8000, Spring :8080, web :3000
```

With Docker: `docker compose -f infra/docker-compose.yml up --build` (PostgreSQL + pgvector,
API, Spring, web). Download the PDFs on the host (`uv run python -m scripts.download_book <id>`),
then index each course once with
`docker compose -f infra/docker-compose.yml run --rm --user root api python -m rag.ingest <id>`
(one-off job as root: the mounted `data/` folder may not be writable by the API's non-root
user). Until a course is indexed, `/chat` answers 503 with that command. The image embeds the
base e5 model; pass `--build-arg EMBEDDING_MODEL=<Hub id>` to use the fine-tuned one.

Tests: `uv run pytest -q` (no network), `cd core; .\mvnw.cmd test`,
`cd frontend; npm test; npm run build`.

## Stack

Python 3.13 (FastAPI, LangGraph, LangChain, sentence-transformers, PyTorch CPU, pypdf, asyncpg),
Gemini `gemini-3.5-flash-lite` with Pydantic structured outputs, PostgreSQL + pgvector (Neon in
development), Next.js 16 + React 19 + react-pdf + Recharts, Spring Boot 4.1 + Java 21, GitHub
Actions, Docker Compose. Design decisions are logged in [DECISIONS.md](DECISIONS.md) and the
measured progress in [JOURNAL.md](JOURNAL.md).

## Attribution

- *Principles of Data Science* by Shaun V. Ault, Soohyun Nam Liao and Larry Musolino (senior
  contributing authors), OpenStax, Rice University, 2025,
  [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Access for free at
  [openstax.org](https://openstax.org/details/books/principles-data-science).
- *Introductory Statistics 2e* by Barbara Illowsky and Susan Dean (senior contributing
  authors), OpenStax, Rice University, 2023,
  [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Access for free at
  [openstax.org](https://openstax.org/details/books/introductory-statistics-2e).
- Fonts: Bricolage Grotesque and Literata, SIL Open Font License 1.1 (`frontend/app/fonts`).

The book PDFs are downloaded locally and never stored in this repository.

## License

Code: [MIT](LICENSE). Files derived from the books (`course/notions/*.json`, `eval/*.json`,
`frontend/demo/data.json`):
CC BY-NC-SA 4.0, see [LICENSE-CONTENT.md](LICENSE-CONTENT.md).
