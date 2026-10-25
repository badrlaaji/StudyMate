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

## Étape 9 — Spring Boot et maîtrise (2026-10-20)
- **Fait** : service Spring Boot 4.1.1 (POST /api/scores, GET /api/notions/weak, GET /api/mastery, schéma `app`) ; carte de maîtrise (tuiles colorées, plan de révision, graphique) ; page quiz (touches 1-4, correction immédiate, page source) ; boucle de bout en bout vérifiée dans Chromium ; `scripts/dev.ps1`.
- **Bloqué** : rien. `dev.ps1` écrit pour Windows, non exécuté ici (environnement Linux).
- **Chiffres** : 11 tests Spring (5 règles + 6 endpoints) ; démarrage 3,4 s ; boucle : Feynman CNN 2/5 enregistré → plan [k-means 1,5 ; CNN 2,0] → quiz sur k-means, CNN + 1 notion au hasard → k-means (5+2+1)/3 = 2,67, CNN (0+2)/2 = 1,0 ; 2 bugs trouvés en vrai (constructeur double, 500 au lieu de 400) ; 0 erreur JS.

## Étape 10 — CI, Docker, mesures (2026-10-20)
- **Fait** : GitHub Actions (python, java, web, compose avec `/health`) ; 3 images non-root (api, core, web) construites et lancées ensemble en compose : base vide → `/chat` 503 avec la commande (bug 500 corrigé) → indexation dans le conteneur → recherche OK ; latence `/chat` et Lighthouse mesurés ; README final.
- **Bloqué** : tag `v1.0` (validations humaines, notes Feynman, vidéo) ; quota AI Studio à relever ; `dev.ps1` non testé sous Windows.
- **Chiffres** : `/chat` médiane 2,73 s, p90 3,17 s (min 2,33, max 5,55 ; 20 appels, dev 19/20 corrects) ; Lighthouse 13.5 : 98-100 en performance, 100 ailleurs (4 mesures) ; images api 2,97 Go, core 557 Mo, web 336 Mo ; indexation en conteneur 284 morceaux en 23 s ; 123 tests Python (122 passés, 1 ignoré), 11 tests Spring ; 1re CI verte : python 54 s (123 tests, base comprise), java 22 s, web 33 s, compose 1 min 58 s.

## Étape 11 — Plusieurs cours, nouvelle interface (2026-10-20)
- **Fait** : registre `course/courses.json` + `course.add` ; `course_id` dans `chunks` et dans les notes Spring (migrations testées) ; 2e cours Introductory Statistics 2e (ch. 12) ajouté et interrogé ; interface refaite (critique, système de design, polices locales OFL, barre latérale + sélecteur de cours, Bibliothèque, mobile, sombre) ; audit d'accessibilité ; règle « réécrire seulement pour traduire » ; `docs/FUNCTIONAL-REQUIREMENTS.md`.
- **Bloqué** : éval complète des réponses à relancer (quota gratuit épuisé : un appel a pris 2 min 30 s) ; catalogue statistics à relire (sections de TP faibles) ; pas de jeu d'éval pour ce cours ; notes Feynman humaines toujours en attente.
- **Chiffres** : statistics : 61 pages, 108 712 caractères, 135 morceaux (embeddings 66 s), 11 notions, 2 min 58 s ; migration : 568 morceaux rattachés, 7 notes locales rattachées par SQL ; réponses (prompts multi-cours) EN 18/20, FR 19/20, pièges 5/5 et 5/5 ; test02 corrigé (page 279 citée) ; axe-core 0 violation (24 combinaisons + 5 états, après 4 défauts corrigés) ; Lighthouse mobile 94-100 en performance, 100 en accessibilité, bonnes pratiques, SEO (carte mobile 87 → 94 avec le graphique chargé à part) ; tests : 144 Python (143 + 1 base), 13 Spring.

## Étape 12 — Importer un manuel depuis l'interface (2026-10-20)
- **Fait** : upload d'un PDF dans la Bibliothèque (chapitres du sommaire ou plage de pages, licence, auteurs, case de droits), traitement en arrière-plan avec suivi, Réessayer, Supprimer ; cours importés dans `data/` ; essai réel dans le navigateur ; 2 défauts corrigés (dernier chapitre, sections de résumé).
- **Bloqué** : rien de nouveau ; l'upload fait confiance à l'utilisateur pour les droits et les données personnelles (case à cocher).
- **Chiffres** : Introduction to Python Programming : 9,96 Mo, 397 pages, 15 chapitres détectés ; chapitre 5 → 22 pages, 33 passages, 5 notions (6 avant la règle des résumés) ; réponse vérifiée p. 125 et 143 ; axe-core 0 violation (formulaire, traitement, 6 pages × 4 variantes) ; Lighthouse Bibliothèque 97/100/100/100 mobile, 100 partout ordinateur ; 158 tests Python (+ 1 base), 13 Spring.

## Étape 13 — Démo publique sans appel LLM (2026-10-25)
- **Fait** : `scripts/build_demo.py` (vrai agent, une fois) → `frontend/demo/data.json` ; `DEMO_MODE=1` : routes `/api/*` et pages servies par Next.js seul, notes dans un cookie, bannière démo, questions et explications d'exemple, lecteur vers openstax.org, Bibliothèque en lecture seule ; Vitest + test « aucune requête sortante » ; `npm test` en CI ; README (héberger la démo).
- **Bloqué** : déploiement public à faire avec le compte de Badr (Vercel ou autre) : lien [X].
- **Chiffres** : démo : 11 réponses (10 vérifiées, 1 refus), 36 questions de quiz, 3 explications notées 3/5, 85 Ko ; cookie au pire 1 765 octets ; parcours Chromium : 0 connexion sortante du serveur, 0 requête externe du navigateur, axe-core 0 violation (8 états) ; tests : 18 Vitest, 164 Python (+ 1 base), 13 Spring.

## Étape 14 — Évaluation de régression en CI (2026-10-25)
- **Fait** : mode hors ligne du LLM (`LLM_OFFLINE`, `LLM_CACHE_DIR`) ; `eval/regression.py` (check / record) ; 112 réponses enregistrées dans `eval/replay/` ; seuils `eval/thresholds.json` ; job CI `eval` (base pgvector, téléchargement du livre, indexation, porte, tableau dans le résumé du job) ; régression volontaire démontrée.
- **Bloqué** : rien. Le fine-tuné ne peut pas être évalué en CI tant qu'il n'est pas publié sur le Hub.
- **Chiffres** : e5 de base, jeu test : hit@4 EN 0,85 / FR 0,75, MRR 0,703 / 0,604 (identiques à l'étape 4 : reproductible) ; réponses EN 16/20, FR 18/20, pièges 5/5 et 5/5 ; enregistrement 11 min (112 appels) ; rejeu hors ligne 21 s, 0 miss ; régression (MiniLM anglais) : FR hit@4 0,60, MRR 0,514, code de sortie 1, et en CI (run 40222183740 : python vert, eval rouge, 6 erreurs) ; CI sur main : mêmes chiffres qu'en local, 0 miss, job eval 103 s ; tests : 173 Python (+ 1 base), 18 Vitest.

## Étape 15 — Répétition espacée FSRS (2026-10-25)
- **Fait** : Spring `GET /api/scores` (historique daté) ; `agent/review.py` (py-fsrs 6.3.2, rejeu des notes) ; `GET /review` ; quiz : notions dues d'abord ; question passée non notée ; carte « Prochaines révisions » sur la page Progression (FR/EN, mobile, sombre).
- **Bloqué** : rien. Démo publique sans FSRS (pas de dates dans le cookie).
- **Chiffres** : 1re note « bonne » le 1er janvier 9 h → révision le 3 ; 2e le 3 → le 14 ; échec le 14 → le 16 (tests à dates fixes) ; base locale : 12 notes du 20 octobre → 4 notions en retard de 3 à 4 jours ; question passée : 12 notes avant, 12 après ; axe-core 0 violation (FR bureau, EN mobile sombre) ; tests : 190 Python (+ 1 base), 16 Spring, 20 Vitest ; porte de régression : 0 miss.

## Étape 16 — Quiz aux gestes et « Passer » (2026-10-25)
- **Fait** : `lib/gestures.ts` (comptage des doigts, stabilisation) ; `GestureCam` (MediaPipe dans le navigateur, caméra désactivée par défaut, anneau de progression, annonces `aria-live`) ; Passer (touche P, bouton, poing 1,5 s) ; résumé des questions passées ; journal `quiz_answer` dans Spring ; CSP qui bloque la télémétrie de MediaPipe ; démo compatible.
- **Bloqué** : pas de vraie main devant une vraie caméra ici : test avec une fausse caméra (vidéo d'une image d'exemple) ; à refaire devant une webcam sous Windows.
- **Chiffres** : fausse caméra « victoire » → réponse 2 en 0,9 s ; poing → question passée en 1,4-1,6 s ; axe-core 0 violation (/quiz caméra active) ; question passée en vrai : 12 → 13 notes (seule la notion répondue), statut SKIPPED en base ; WASM 13 Mo (+ 12 Mo de secours sans SIMD) servis par le site, modèle 7,8 Mo ; tests : 193 Python (+ 1 base), 22 Spring, 34 Vitest.

### Quota Gemini (AI Studio → Rate limit, offre gratuite)
| Modèle | Requêtes/min | Requêtes/jour | Tokens/min | Relevé le |
| --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | [X] | [X] | [X] | [X] |
