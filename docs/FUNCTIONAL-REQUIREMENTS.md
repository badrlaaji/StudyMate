# Functional requirements: what StudyMate solves, and the evidence

Each need is checked by an automated test, a measured run, or a real journey in the browser
(Playwright, production build, real Gemini calls). Status: ✅ met and verified, ⚠️ met with a
limit, ❌ not met. Last checked: 2026-10-20.

| # | A student needs to… | How StudyMate does it | Evidence | Status |
| --- | --- | --- | --- | --- |
| F1 | Ask about the course in English or French and get an answer in that language | Router detects the language and rewrites the search query in the book's language | Agent on 20 test questions per language: 18/20 English, 19/20 French correct with a verified citation on an expected page; French screenshots | ✅ |
| F2 | Trust the answer | Every cited page must be among the retrieved pages (code check), else 1 retry, else "not in this course" | `test_verify_citations*`, `test_graph_*` (pytest); traps refused 5/5 in each language | ✅ |
| F3 | See the source | The cited PDF page opens next to the chat, passage highlighted | Browser journey: page 327 opened, 2 highlighted lines; axe 0 violations on that state | ✅ |
| F4 | Not be misled outside the course | Out-of-course questions are refused, also across courses | 5 traps refused per language; "random forest" refused in the statistics course, answered p. 327 in data science | ✅ |
| F5 | Ask for a quiz or a plan in plain words | LangGraph router (answer / quiz / plan), keyword fallback if the LLM fails | `test_fallback_route`, `test_route_message_*`, `test_graph_plan_from_spring` | ✅ |
| F6 | Check their own understanding (Feynman) | LLM judges each key idea; code computes the 0-5 score; follow-up question and pages | Formula tests (6 cases); journey: k-means explanation → 3/5, 2 ideas covered, 1 missing | ⚠️ judge vs human agreement not measured yet (20 blind grades pending) |
| F7 | Know what they master | Average of the last 3 scores per notion; weak < 3, mastered ≥ 4 (Spring) | 13 Spring tests; progress page shows levels with icon + label | ✅ |
| F8 | Know what to review next | Revision plan without LLM: weakest notions with pages | `test_build_plan_*`, `test_plan_without_llm`; "Review next" cards | ✅ |
| F9 | Practise on weak spots | Quiz on weak notions (Spring), MCQ anchored on their pages, graded by code, keys 1-4 | `test_notion_scores_graded_by_code`, quiz tests; journey: key 1 → "Correct!", source p. 364 | ✅ |
| F10 | Study other textbooks | Upload a PDF in the library (chapters from its outline or a page range), or the course registry + `course.add <id>`; index, notions and scores separated per course | Browser journey: *Introduction to Python Programming* uploaded, chapter 5 → 33 passages, 5 notions, verified answer (p. 125, 143), deleted and uploaded again; Statistics 2e ch. 12 by command (135 passages, 11 notions); API tests for upload, processing, retry, delete | ⚠️ new catalogues are LLM drafts to review |
| F11 | Use the app in French | FR/EN dictionaries, cookie, French typography | French screenshots; same pages in both languages | ✅ |
| F12 | Keep studying when a service is down | Degraded mode: answers still work when Spring is down; 503 with the fix when the course is not indexed or Gemini is unavailable | `test_graph_quiz_in_degraded_mode_*`, `test_chat_without_index_is_a_clear_503`; compose run on an empty database | ✅ |
| F13 | Use it with a keyboard or a screen reader | Skip link, visible focus, "/" shortcut, `aria-live` results, labelled controls | axe-core (WCAG 2.2 AA rules): 0 violations, 6 pages × light/dark × desktop/mobile + 3 dynamic states; keyboard tour | ✅ |
| F14 | Study on a phone, at night | Responsive layout with bottom tab bar; dark theme | Screenshots at 390 px; no horizontal scroll at 200 % zoom | ✅ |
| F15 | Respect the books' licenses | Attribution in the sidebar and README; PDFs never in Git; non-commercial terms | `LICENSE-CONTENT.md`; course attribution from the registry | ✅ |

## Not covered (by design or not yet)

- **One learner per installation**: no accounts; scores are per course, not per person
  (local demo, the Gemini free tier forbids a public deployment for EU/UK users).
- **Uploads trust the user**: the interface asks to confirm the right to use the document
  and that it holds no personal data, but cannot check it (its text is sent to Gemini).
- **The statistics course has no evaluation set**: its quality was only spot-checked
  (3 questions, pages read by hand).
