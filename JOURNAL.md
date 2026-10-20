# Journal

Format : 3 lignes par étape (fait, bloqué, chiffres mesurés).

## Étape 0 — Repo et environnement (2026-10-20)
- **Fait** : venv uv Python 3.13 ; torch CPU (`cuda.is_available() = False`) ; e5 chargé avec préfixes ; Neon via asyncpg depuis Windows : `CREATE EXTENSION vector` OK, TLS obligatoire vérifié ; Gemini `gemini-3.5-flash-lite` → réponse Pydantic valide (`json_schema`, `thinking_level=minimal`) ; dépendances figées (wheels Windows cp313 vérifiées) ; tests verts.
- **Bloqué** : quota AI Studio à relever.
- **Chiffres** : Python 3.13.16 ; uv 0.13.3 (Windows) / 0.11.32 (Linux) ; torch 2.14.1+cpu ; 94 paquets runtime / 98 dev (132 au total) ; e5 : dim 384, cosinus 0,9066 (passage pertinent) vs 0,7730 (hors sujet) ; Neon : PostgreSQL 18.6 + pgvector 0.8.6 ; base locale/CI : PostgreSQL 17.10 + pgvector 0.8.2 ; `check_env all` en 42 s (Linux, modèle en cache) ; 8 tests passés.

## Étape 1 — Livre → pages (2026-10-20)
- **Fait** : PDF officiel téléchargé ; `pages.jsonl` des chapitres 6-7 (numéros de page PDF, section, texte nettoyé) ; 0 pied de page restant ; chapitre 7 relu par échantillon (4 pages comparées au rendu du PDF : prose et tableaux fidèles) + contrôles automatiques sur toutes les pages.
- **Bloqué** : rien. Limite : formules perdues (dessinées dans le PDF).
- **Chiffres** : PDF 569 pages, 37,3 Mo ; chapitre 6 = 66 pages, 129 116 caractères ; chapitre 7 = 45 pages non vides (1 page blanche écartée), 116 340 caractères ; total 111 pages, 245 456 caractères ; 39/111 pages avec ≥ 3 traces de formule perdue ; ingestion en 3 s ; 22 tests passés.

## Étape 2 — Catalogue de notions (2026-10-20)
- **Fait** : schéma Pydantic du catalogue ; brouillon par `gemini-3.5-flash-lite` (1 appel par section) ; relecture : 4 défauts au 1er essai → prompt corrigé → 0 défaut aux contrôles, + 3 corrections à la main ; cache LLM et politique 429 ; `LICENSE-CONTENT.md`.
- **Bloqué** : validation du catalogue par Badr (D1) — `"validated": false` en attendant.
- **Chiffres** : 21 notions issues des 10 sections numérotées, 2 à 8 pages par notion, 3 à 5 idées clés ; 20 appels Gemini (2 générations × 10), 1 min 30 par génération (pause 6 s incluse), 0 erreur 429 ; 45 tests passés.

## Étape 3 — Indexation (2026-10-20)
- **Fait** : découpage en tokens e5 (D9), vecteurs « passage: », table `chunks` (pgvector) remplie, recherche top-k cosinus ; 3 recherches vérifiées à la main (EN, FR, paraphrase) ; tests des préfixes verts ; 1 bug trouvé par les tests (INSERT vide).
- **Bloqué** : remplissage de Neon à lancer depuis Windows (`uv run python -m rag.ingest`) : l'environnement Linux n'atteint pas Neon. Base locale pgvector remplie.
- **Chiffres** : 284 morceaux (249 tokens en moyenne, max 300, 1 à 5 par page) ; vectorisation 21 s sur CPU (Linux 4 cœurs) ; recherches manuelles : bonne page dans le top 4 pour 3/3, en 1re position pour 1/3 (EN random forest) — FR rétropropagation : 1re bonne page au rang 3 ; paraphrase surapprentissage : rang 4 ; 58 tests passés (dont 1 avec base).

## Étape 4 — Évaluation de la recherche (2026-10-20)
- **Fait** : 35 questions bilingues (10 dev, 20 test, 5 pièges) ; `eval_retrieval` (hit@4, MRR@10, sans LLM) ; 3 réglages sur dev ; test lancé une fois ; tableau dans le README ; trou du catalogue repéré (pages 279-280 : exactitude, précision, rappel sans notion).
- **Bloqué** : relecture des questions par Badr (`"validated": false`).
- **Chiffres** : dev EN hit@4 1,000 / MRR 1,000, FR 0,900 / 0,775 (identique sans fin de chapitre ; sans préfixe : EN MRR 0,950, FR 0,833) ; **test EN hit@4 0,850 / MRR 0,703 ; FR 0,750 / 0,604** (écart +0,099) ; top-1 pièges 0,746-0,862 vs questions 0,814-0,900 (test) ; 67 tests passés.

## Étape 5 — Fine-tuning (2026-10-20)
- **Fait** : 568 paires EN/FR par Gemini ; décontamination (8 retirées) ; entraînement MNRL sur CPU ; réindexation sous un 2e `embedding_model` ; test base vs fine-tuné ; fiche du modèle et script de publication.
- **Bloqué** : publication sur le Hub → il faut `HF_TOKEN` (écriture).
- **Chiffres** : 57 appels Gemini en 7 min 44 (0 erreur 429) ; 560 paires gardées ; 70 pas (2 époques, lot 16) en 414 s sur CPU Linux 4 cœurs ; modèle 466 Mo ; test base → fine-tuné : EN hit@4 0,850 → 0,950, MRR 0,703 → 0,722 ; FR hit@4 0,750 → 0,800, MRR 0,604 → 0,611 ; 73 tests passés.

## Étape 6 — Agent LangGraph (2026-10-20)
- **Fait** : graphe routeur → answer (recherche, génération, vérification des citations, 1 nouvel essai, not_found) | quiz | plan ; réécriture de la requête en anglais par le routeur ; champ `found` ; nouvel essai après 5xx ; client Spring + mode dégradé ; éval des réponses ; tests sans réseau.
- **Bloqué** : rien (Spring arrive à l'étape 9 ; mode dégradé en attendant).
- **Chiffres** : test (modèle fine-tuné) EN correct 19/20, refus 5/5 ; FR correct 19/20, refus 5/5 ; bonne page dans le top 4 : 19/20 dans les deux langues (FR sans réécriture : 16/20) ; latence médiane 8,3 s EN (pendant des 503 Gemini) / 2,8 s FR ; 1 repli du routeur sur les règles (503) ; ~110 appels Gemini ; 101 tests passés.

## Étape 7 — API, RAGAS, Feynman (2026-10-20)
- **Fait** : FastAPI complète (health, chat, notions, feynman, quiz, quiz/result, mastery, plan, book.pdf) ; juge Feynman + note calculée par le code ; RAGAS ; jeu Feynman à l'aveugle (20 explications) ; Dockerfile de l'API ; parcours réel vérifié dans Chromium (question → réponse vérifiée → page 327 ouverte et passage surligné).
- **Bloqué** : accord Feynman ±1 → il faut les 20 notes humaines à l'aveugle (Badr).
- **Chiffres** : RAGAS (20 questions test EN, juge = gemini-3.5-flash-lite) fidélité 0,934, pertinence 0,931 ; 15/20 réponses à fidélité 1,0 ; plus basse 0,67 (test10, la réponse fausse de l'étape 6) ; ~60 appels Gemini ; 122 tests (121 passés, 1 ignoré sans base de test).

## Étape 8 — Study Desk (2026-10-20)
- **Fait** : Next.js 16 (App Router) : `/study` (chat + PDF, page citée ouverte et passage surligné), `/feynman`, bouton FR/EN, proxy `/api/*`, style papier et encre, raccourci `/`, `aria-live` ; vérifié dans Chromium (0 erreur JS) ; captures dans le README.
- **Bloqué** : vidéo v1 (à tourner par Badr). Carte et quiz : étape 9.
- **Chiffres** : `next build` OK (6 routes) ; PDF 37,3 Mo relayé par le proxy ; surlignage : 4 éléments marqués (seuil 4) → 2 (seuil 15) ; Feynman réel : 2 idées sur 3 → 3/5 ; 80 paquets npm.

### Quota Gemini (AI Studio → Rate limit, offre gratuite)
| Modèle | Requêtes/min | Requêtes/jour | Tokens/min | Relevé le |
| --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | [X] | [X] | [X] | [X] |
