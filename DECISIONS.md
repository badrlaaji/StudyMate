# Décisions

Format : contexte, options, choix, pourquoi (5 lignes max par décision).

## Étape 0 — Repo et environnement

### S0-1 Paramètre SSL d'asyncpg pour Neon
- Contexte : Neon donne `?sslmode=require&channel_binding=require` (format libpq, prévu pour psycopg).
- Mesuré : avec SQLAlchemy 2.1.5, `sslmode` dans l'URL → `TypeError: connect() got an unexpected keyword argument 'sslmode'`. En asyncpg direct, la chaîne complète se connecte à Neon.
- Mesuré : `ssl='disable'` → Neon refuse (`connection is insecure`) : TLS obligatoire, donc `ssl="require"` chiffre bien.
- Lu dans asyncpg 0.32.0 : le channel binding est désactivé volontairement (`protocol/scram.pyx`) ; `channel_binding=require` est ignoré, pas appliqué.
- Choix : `postgresql+asyncpg://…?ssl=require`, sans `channel_binding` (il ne protège rien avec asyncpg). En asyncpg direct : `asyncpg.connect(dsn, ssl="require")`.

### S0-2 Nom de la variable de la clé Gemini
- Choix : `GOOGLE_API_KEY`. Vérifié dans le code de langchain-google-genai 4.4.2 : `GOOGLE_API_KEY` est lue en premier, `GEMINI_API_KEY` en secours.

### S0-3 Méthode de sortie structurée
- Options : `json_schema` (défaut), `function_calling`, JSON brut validé par Pydantic.
- Choix : `with_structured_output(Schema, method="json_schema")`. Réponse valide au premier essai avec `gemini-3.5-flash-lite`.
- Plan B gardé dans `scripts/check_env.py` : `function_calling`. Plan C (JSON brut) inutile pour l'instant.

### S0-4 Réglages du client Gemini (`agent/llm.py`)
- `thinking_level="minimal"` : niveau le plus bas listé par la bibliothèque, accepté par le modèle (mesuré).
- `max_retries=1` : une seule requête. D'après la doc du code, `0` veut dire « défaut Google » (5 essais), qui consommeraient le quota en silence. Nos 429 seront gérés par notre code (étape 6).
- Température non fixée : la bibliothèque la met à `None` pour Gemini 3+ (bonne pratique Google).

### S0-5 Gel des dépendances
- Contexte : runtime et dev figés séparément → conflit (`datasets` 5.1 veut `fsspec<=2026.7.0`, le runtime seul prend 2026.9.0).
- Choix : une résolution commune (`requirements.in` + `requirements-dev.in`) pour Windows, wheels seulement, puis deux fichiers contraints par elle. Bornes basses dans les `.in` : sans elles, uv retombait sur ragas 0.3.2, datasets 1.2.1, langchain-google-genai 3.2.0.
- torch s'installe **d'abord** depuis l'index CPU, puis le reste. Sous Linux, torch de PyPI tire CUDA (wheel de 555 Mo + paquets nvidia).
- Les mêmes fichiers marchent sous Linux : seules différences `colorama` et `tzdata` (pur Python).

### S0-6 Lecture du `.env` sans dépendance
- Options : python-dotenv (hors liste) ; petit lecteur maison.
- Choix : `config.py` (`parse_env` pure et testée, `load_env`, `get_env`). Les variables déjà définies dans le shell sont prioritaires.

### S0-7 Base locale quand Neon est injoignable
- Contexte : un environnement Linux de développement sans DNS ni sortie TCP directe ne peut pas joindre Neon.
- Choix : conteneur `pgvector/pgvector:0.8.2-pg17` (même image que la CI) pour coder et tester. Neon reste la base de développement (W2) ; vérification depuis Windows avec `check_env db`.

### S0-8 Versions Postgres : Neon ≠ CI
- Mesuré : Neon = PostgreSQL 18.6 + pgvector 0.8.6 ; image CI/compose figée = PostgreSQL 17 + pgvector 0.8.2.
- Options : changer l'image CI ; garder l'image figée.
- Choix : garder `pgvector/pgvector:0.8.2-pg17`. On n'utilise que le type `vector`, la distance cosinus `<=>` et l'index HNSW, présents dans les deux versions.

### S0-9 Configuration des outils sans `pyproject.toml`
- Choix : `pytest.ini` (`pythonpath = .`) et `ruff.toml`.
- Pourquoi : un `pyproject.toml` à la racine change le comportement de `uv run` (mode projet) ; on reste sur `requirements.txt` comme prévu (inférence).

## Étape 1 — Livre → pages

### S1-1 Bornes des chapitres lues dans les signets du PDF
- Options : pages écrites en dur ; recherche de « Chapter 6 » dans le texte ; signets (outline) du PDF.
- Choix : signets via pypdf → chapitre 6 = pages PDF 275-340, chapitre 7 = 341-386 (fin = début du chapitre suivant − 1).
- Pourquoi : source structurée, exacte, et le titre de section de chaque page vient au passage.

### S1-2 D8 précisé : comment compter les lignes répétées
- Constat (mesuré) : sur les 112 pages, aucune ligne ne dépasse 50 % (« Access for free at openstax.org » = 50 % pile, pied de chapitre = 27 %), car les en-têtes alternent pages paires / impaires.
- Choix : la règle des 50 % est appliquée par chapitre et par parité, chiffres remplacés par `#` (le numéro de page change). Plus une règle de forme pour le pied des pages impaires (titre de section + numéro), qui change à chaque section.
- Résultat : 0 pied de page restant dans `pages.jsonl`.

### S1-3 Garder toutes les pages du chapitre, avec leur section
- Options : couper après « Key Terms » ; tout garder.
- Choix : tout garder (exercices et références compris) avec le champ `section`. Filtrer ou non ces pages = un réglage à comparer à l'étape 4.

### S1-4 Formules absentes du texte (limite connue)
- Constat : les formules sont dessinées (aucune police mathématique sur la page ; `pdftotext` donne le même résultat). Indicateur : 39 pages sur 111 avec au moins 3 traces de formule perdue.
- Options écartées pour la v1 : OCR (lent, hors liste), version HTML d'OpenStax avec MathML (pas de numéros de page PDF, contraire à D8).
- Atténuation : le panneau PDF affiche la vraie page citée.

## Étape 2 — Catalogue de notions

### S2-1 Un appel LLM par section, nombre de notions proportionnel
- Options : un seul appel pour 111 pages ; un appel par page ; un appel par section numérotée.
- Choix : un appel par section (10 appels), 1 notion pour ~5 pages, entre 1 et 4 → 21 notions (D1 : 15 à 25).
- Pourquoi : chaque appel voit un texte cohérent avec ses marqueurs `[page N]` ; le code garde seulement les pages de la section.

### S2-2 Le code contrôle ce que le LLM propose
- Schéma Pydantic : id en snake_case, 3 à 5 idées clés EN/FR, 15 à 25 notions, ids uniques.
- Pages citées ∩ pages de la section ; une notion sans page valide est rejetée (pas de « page devinée »).

### S2-3 Prompt corrigé après relecture
- 1re génération : 4 défauts relevés (accents absents dans la section 6.1, majuscules à l'anglaise, idées formulées en consignes, « surajustement » / « surapprentissage » mélangés).
- Choix : règles explicites dans le prompt + mini-glossaire FR → 0 défaut aux contrôles automatiques. Puis 3 corrections à la main (nom DBSCAN, « k-means », « rééchantillonnage »).

### S2-4 Appels LLM : cache disque + politique 429 (`agent/llm.py`)
- `invoke_structured()` : cache sha256(modèle + prompt) dans `.cache/llm/`, puis 1 seul nouvel essai après un 429 (délai lu dans l'erreur, sinon 60 s), puis message clair.
- On attrape `langchain_core.exceptions.ModelRateLimitError` (générique, parent de l'erreur Gemini) : un futur fournisseur (Groq) passe par le même code.

### S2-5 Validation humaine (D1) non bloquante
- `notions.json` est commité avec `"validated": false`. Le script de brouillon refuse d'écraser un catalogue validé.

## Étape 3 — Indexation

### S3-1 SQL direct plutôt que langchain-postgres
- Options : `PGVectorStore` de langchain-postgres ; SQL écrit à la main (SQLAlchemy async + asyncpg).
- Choix : SQL direct (`rag/store.py`, 4 requêtes lisibles).
- Pourquoi : langchain-postgres attend un objet `Embeddings` (une classe à écrire, contraire aux règles de code) et impose son schéma de table. langchain-postgres reste installé (stack figée) mais n'est pas utilisé.

### S3-2 Recherche exacte, sans index
- Options : index HNSW (approché) ; parcours complet (exact).
- Choix : pas d'index. 284 morceaux : le parcours complet prend quelques millisecondes et le résultat est exact. Un index HNSW se justifierait à partir de dizaines de milliers de lignes.

### S3-3 Colonne `embedding_model`
- Une seule table `chunks`, une colonne qui dit quel modèle a produit le vecteur : e5 de base et e5 fine-tuné (étape 5) cohabitent et se comparent sans changer le schéma.

### S3-4 Morceaux = tranches exactes de la page, longueur garantie
- Le texte d'un morceau est coupé dans la page grâce aux positions de caractères du tokenizer (pas de texte reconstitué).
- Mesuré : 12 morceaux sur 284 faisaient 301 tokens une fois retokenisés avec le préfixe → boucle qui retire un token en fin de morceau jusqu'à ≤ 300. Résultat : max 300.

### S3-5 Vecteurs passés en texte avec `CAST(... AS vector)`
- Évite un paquet Python supplémentaire (hors liste) pour enregistrer le type `vector` dans asyncpg.

### S3-6 Test de base de données optionnel
- `tests/test_rag.py` contient un test sur une vraie base, lancé seulement si `TEST_DATABASE_URL` est défini : les tests par défaut n'utilisent pas le réseau. La CI (étape 10) le lancera avec le conteneur pgvector.

## Étape 4 — Évaluation de la recherche

### S4-1 Questions écrites sans le LLM de l'application
- Options : générer les questions avec Gemini ; les écrire en lisant les pages.
- Choix : écrites en lisant les pages, reformulées (pas de copie du livre), pages attendues vérifiées par recherche de mots-clés dans le texte. À relire par Badr (`"validated": false`).
- Pourquoi : Gemini générera les paires du fine-tuning (étape 5) ; des questions de test dans le même style gonfleraient le gain mesuré.

### S4-2 Mesures
- hit@4 (une bonne page dans les 4 premiers morceaux) et MRR@10 (1/rang de la 1re bonne page, 0 au-delà de 10). Une question peut avoir plusieurs pages attendues.

### S4-3 Réglages comparés sur dev, puis test lancé une fois
- `all-pages` = `no-end-matter` (identiques sur dev) → on garde toutes les pages : pas de filtre.
- `no-query-prefix` : EN MRR 1,000 → 0,950, FR 0,775 → 0,833. Écart = 1 question sur 10 : dans le bruit. On garde le préfixe (fiche du modèle, règle du projet, cohérence avec le fine-tuning).
- Limite reconnue : dev (questions directes) est trop facile (EN 1,000) pour départager ; test (paraphrases) est plus dur.

### S4-4 Pas de seuil de score pour les questions hors cours
- Mesuré : top-1 des pièges 0,746-0,862 ; top-1 des vraies questions 0,799-0,905. Les plages se chevauchent → le refus se fera par l'agent (citations vérifiées), pas par un seuil.

## Étape 5 — Fine-tuning des embeddings

### S5-1 `old_fit` plutôt que le Trainer
- Constat : `SentenceTransformerTrainer` lève `ImportError: … requires accelerate>=1.1.0` ; accelerate n'est pas dans la stack.
- Options : ajouter accelerate (dépendance hors liste) ; `old_fit` (boucle PyTorch documentée dans sentence-transformers 6.1.0).
- Choix : `old_fit` + `NoDuplicatesDataLoader` + `MultipleNegativesRankingLoss` (F1). Aucune dépendance ajoutée.

### S5-2 Paires synthétiques EN + FR
- 5 morceaux par appel (F1) → 57 appels, 1 question EN + 1 FR par morceau = 568 paires. Contrôles : 0 formulation « ce passage », aucune suite de 8 mots copiée du livre.
- `NoDuplicatesDataLoader` : la question EN et la question FR d'un même passage ne sont jamais dans le même lot (sinon fausses négatives).

### S5-3 Décontamination
- Mesuré : 5 questions de test sur 40 avaient une question générée à ≥ 0,95 de similarité (même idée, même formulation naturelle).
- Choix : retirer toute paire à ≥ 0,95 d'une question dev ou test → 8 paires retirées, 560 gardées.

### S5-4 Résultat et choix du modèle de l'application
- Test : hit@4 EN 0,850 → 0,950, FR 0,750 → 0,800 ; MRR@10 EN 0,703 → 0,722, FR 0,604 → 0,611. Par question : 6 gagnent / 5 perdent (EN), 5 / 5 (FR). Dev : EN MRR 1,000 → 0,920, FR 0,775 → 0,860.
- Lecture : gain en hit@4 (ce que l'agent utilise : top 4), pas de gain démontré en MRR. 20 questions : indicatif.
- Choix : l'application utilisera le modèle fine-tuné une fois publié sur le Hub (`EMBEDDING_MODEL` = id du Hub) ; e5 de base par défaut d'ici là.
- Observation : les scores du modèle fine-tuné s'étalent (pièges 0,25-0,40, questions 0,37-0,78), sans séparer parfaitement (4/40 questions sous 0,41) → S4-4 inchangé.

## Étape 6 — Agent LangGraph

### S6-1 Le nouvel essai est une arête du graphe
- `generate` → `after_generate` (fonction pure) → `answered` | `generate` (1 nouvel essai) | `not_found`. État Pydantic (pas de classe hors schémas) ; dépendances (base, Spring, LLM) injectées dans `build_graph` → tests avec des faux.

### S6-2 Le routeur réécrit aussi la requête en anglais (`search_query`)
- Constat : en français, la recherche ramenait moins souvent la bonne page (top 4 : 16/20 avec le modèle fine-tuné).
- Choix : un champ de plus dans la sortie structurée du routeur (même appel, 0 appel en plus) ; les règles de secours gardent le message tel quel.
- Mesuré : top 4 en français 19/20 dans l'agent (anglais 19/20).

### S6-3 Champ `found` dans la réponse
- Constat (essai réel) : réponse « Le texte ne mentionne pas pourquoi… » avec une page citée → acceptée par la vérification. Choix : `found: bool` obligatoire ; `found = false` → `not_found`.

### S6-4 Nouvel essai aussi après une erreur 5xx
- Constat : 503 « high demand » de Gemini pendant l'éval. Choix : même politique que le 429 (`ModelAPIError` de langchain-core) : attendre, 1 nouvel essai, message clair.

### S6-5 Appels LLM synchrones dans des threads
- `invoke_structured` est synchrone (cache disque) ; dans les nœuds async, `asyncio.to_thread` évite de bloquer la boucle d'événements (et FastAPI).

### S6-6 Contrat Spring figé maintenant, mode dégradé
- `GET /api/notions/weak`, `GET /api/mastery`, `POST /api/scores`. Spring absent → quiz sur des notions au hasard (`status: degraded`), plan vide, score non enregistré (journalisé).

### S6-7 Arrondi « au demi supérieur » (précision de D2)
- `round()` de Python arrondit au pair (2,5 → 2). Choix : `round_half_up` (2,5 → 3) pour la note Feynman et les notes de quiz.

### S6-8 « Correcte » sans juge LLM
- Correcte = statut `ok` + citation vérifiée sur une page attendue. La qualité du texte sera mesurée par RAGAS (étape 7).

## Étape 7 — API, RAGAS, juge Feynman

### S7-1 FastAPI : dépendances dans `app.state`, ouvertes au démarrage
- `lifespan` ouvre le pool SQL, le client Spring, charge le catalogue, compile le graphe et précharge le modèle d'embeddings. Les tests remplissent `app.state` avec des faux (pas de lifespan) → 1 test par endpoint, sans réseau.
- LLM indisponible deux fois de suite → `RuntimeError` → réponse 503 claire (gestionnaire d'exception), pas une erreur 500.

### S7-2 RAGAS 0.4.3 avec la stack figée
- Constat 1 : `import ragas` échoue (`langchain_community.chat_models.vertexai` n'existe plus dans langchain-community 0.4.2) ; revenir à langchain-community 0.3 est impossible (exige langchain-core < 1).
- Choix 1 : module de remplacement vide avant l'import (ragas ne s'en sert que dans une liste `isinstance` pour d'anciens modèles LangChain, chemin non utilisé). Aucune version changée.
- Constat 2 : l'adaptateur Google de ragas exige un client synchrone, alors que ses métriques sont asynchrones. Choix 2 : point d'entrée compatible OpenAI de Gemini (`v1beta/openai/`) avec le client `openai` déjà installé.
- `strictness=1` pour la pertinence (3 par défaut) : 3 appels par question au lieu de 5 (quota). Cache disque de ragas pour les relances.

### S7-3 Juge Feynman : protocole à l'aveugle
- 20 explications de qualité variée (EN/FR), écrites sans le LLM de l'application. Le script refuse de tourner tant que les 20 notes humaines ne sont pas saisies : la personne qui note ne voit jamais la note du code avant.

### S7-4 Image Docker de l'API
- `python:3.13-slim`, torch depuis l'index CPU puis le lock, modèle d'embeddings intégré à l'image (`ARG EMBEDDING_MODEL`), utilisateur non root, `.dockerignore` (ni données, ni modèles, ni secrets).

## Étape 8 — Interface « Study Desk »

### S8-1 Un seul proxy `/api/[...path]` avec liste blanche
- Le navigateur n'appelle que Next.js ; la route relaie vers `API_URL` (côté serveur seulement) les 9 chemins autorisés, 404 pour le reste (vérifié : `/api/secret` → 404).

### S8-2 Langue : cookie + 2 dictionnaires
- `i18n/en.json`, `fr.json` ; le bouton écrit le cookie `lang` puis `router.refresh()` : les pages serveur relisent le cookie. Pas de bibliothèque d'i18n.

### S8-3 PDF : chargé à la demande, passage surligné
- `next/dynamic` sans rendu serveur ; worker configuré dans le même module que `<Document>` (doc react-pdf 10). Plan B : lien `book.pdf#page=N`.
- Surlignage : un élément de texte de la page est marqué s'il fait partie de l'extrait cité. Mesuré : avec un seuil de 4 caractères, des mots isolés (« random forest ») étaient surlignés ailleurs ; seuil 15 → seules les 2 lignes de l'extrait.

### S8-4 Étapes d'attente affichées au minuteur
- Pas de streaming (les citations sont vérifiées avant affichage) : « recherche → rédaction → vérification » suivent le temps écoulé, pas l'état réel de l'agent. Approximation assumée.

### S8-5 TypeScript 5.9.3
- TypeScript 7.0 (réécriture native) existe ; sa compatibilité avec Next 16 n'a pas été vérifiée → 5.9.3. Versions exactes dans `package.json` + `package-lock.json`.

## Étape 9 — Spring Boot et maîtrise

### S9-1 Projet Spring Initializr, Boot 4.1.1
- Java 21, Maven (wrapper `mvnw`/`mvnw.cmd`), web, data-jpa, validation, pilote PostgreSQL. Boot 4 : starters de test par module (`webmvc-test`, `data-jpa-test`), Jackson 3 (`tools.jackson`).

### S9-2 Règles de maîtrise dans des fonctions pures
- `summarize` (moyenne des 3 dernières notes, arrondie à 2 décimales) et `level` (WEAK < 3 ≤ LEARNING < 4 ≤ MASTERED) sont statiques et testées sans Spring ni base.

### S9-3 Tests sans base de données
- Pas de H2 ni de Testcontainers (hors liste) : tests unitaires des règles + `@WebMvcTest` avec le service simulé (1 test par endpoint). Le test `contextLoads` généré (qui exige une base) est retiré.
- Limite vécue : ces tests n'ont pas vu un démarrage impossible (deux constructeurs dans `MasteryService`, Spring ne savait pas lequel choisir). Corrigé (un seul constructeur) ; la CI (étape 10) démarrera le service avec une vraie base.

### S9-4 Validation des paramètres par Spring MVC
- `@Validated` sur la classe faisait passer `limit=0` par la validation AOP → `ConstraintViolationException` → 500. Sans lui, Spring MVC valide les paramètres annotés lui-même → 400 (mesuré par le test).

### S9-5 Schéma `app` créé par Hibernate
- `ddl-auto=update` + `default_schema=app` + `create_namespaces=true` : une seule table, pas d'outil de migration (Flyway hors liste). Les morceaux restent dans `public`.

### S9-6 Interface : couleurs non seules, pas d'animation
- Quiz : ✓/✗ écrits en plus de la couleur ; options répondues sans opacité réduite (contraste). Graphique Recharts sans animation (mesuré : une capture prise pendant l'animation montrait des barres fausses).

## Étape 10 — CI, Docker, mesures

### S10-1 CI en 4 tâches
- `python` (ruff + pytest, avec un service pgvector : le test de base tourne aussi), `java` (`mvnw test`), `web` (typecheck + build), puis `compose` : les 3 images sont construites et la pile démarre ; `/health` doit renvoyer `database: true` **et** `spring: true`.
- Le dernier contrôle est le test de démarrage réel qui manquait aux tests Spring (S9-3).

### S10-2 Trois images
- api : torch CPU + modèle intégré (2,97 Go, mesuré) ; core : build Maven puis JRE 21 seul (557 Mo) ; web : sortie `standalone` de Next.js (336 Mo). Les trois tournent sans root.

### S10-3 Base vide au premier démarrage du compose
- Le livre n'est jamais dans une image : `scripts.download_book` puis `docker compose … run --rm --user root api python -m rag.ingest` remplissent la base. La CI ne teste que le démarrage et `/health`.
- `--user root` pour cette tâche ponctuelle seulement : testé, l'utilisateur non-root ne pouvait pas écrire dans `data/` monté (dossier appartenant à root sur l'hôte). L'API elle-même reste non-root.

### S10-4 Latence mesurée sur des questions jamais posées
- Les 20 questions dev (EN + FR) n'étaient pas dans le cache LLM : la latence de `/chat` mesurée est celle d'appels Gemini réels (routeur + réponse), pause de quota exclue.

### S10-5 Tag v1.0 après les validations humaines
- Le tag `v1.0` attend : validation de `notions.json` et des questions d'éval (`validated: true`), notes Feynman à l'aveugle, vidéo. Tout le reste est livré et mesuré.

### S10-6 Index absent : 503 avec la commande, pas 500
- Testé en compose sur une base vide : `/chat` renvoyait 500 (`relation "chunks" does not exist`). Options : créer la table au démarrage (réponse « introuvable » trompeuse, 2 appels LLM perdus) ou un 503 explicite. Choix : gestionnaire `ProgrammingError` → 503 « Run python -m rag.ingest », l'erreur SQL complète va dans les logs.

## Étape 11 — Plusieurs cours, nouvelle interface

### S11-1 Registre des cours plutôt qu'un livre écrit en dur
- Le livre, les chapitres 6-7 et le catalogue étaient fixés dans une dizaine de fichiers. Options : une base ou une table par cours, ou une colonne `course_id`. Choix : `course/courses.json` (id, titre, PDF, licence, chapitres ou pages) + `course_id` dans `chunks` et dans les notes Spring. Une seule table, une recherche filtrée, et aucun code à toucher pour ajouter un cours.
- Ajout en une commande : `python -m course.add <id>` (téléchargement, indexation, brouillon des notions). Un catalogue existant n'est jamais réécrit.

### S11-2 Migration sans outil de migration
- Table `chunks` existante : `ALTER TABLE … ADD COLUMN IF NOT EXISTS course_id … DEFAULT '<cours par défaut>'` (les anciennes lignes étaient toutes du cours de référence ; testé sur la base locale : 568 lignes rattachées). Spring : colonne nullable (Hibernate `update` ne peut pas ajouter un NOT NULL sur une table remplie) ; la validation de la requête impose le cours.

### S11-3 D1 assoupli pour les autres cours
- 15 à 25 notions reste vrai et testé pour le cours de référence. Un chapitre de 60 pages en donne 11 : le schéma accepte 3 à 40.

### S11-4 Prompts sans livre en dur
- Titre du livre dans le prompt de réponse ; le routeur réécrit la recherche dans la langue du livre (`book_lang`). Les chiffres d'éval du README ont été mesurés avec l'ancien prompt (même pipeline, texte du titre différent).

### S11-5 Pas d'upload dans l'interface (D6 conservé)
- Un upload enverrait n'importe quel document à Gemini (offre gratuite : contenu réutilisable par Google), prendrait des minutes et du quota. Ajout par la ligne de commande, avec la licence écrite dans le registre.

### S11-6 Interface : système de design et contrôles mesurés
- Critique de l'ancienne interface, puis jetons CSS (neutres, un accent violet, 3 statuts), polices locales OFL (Bricolage Grotesque, Literata), icônes SVG maison (pas de dépendance). Couleurs de statut validées par script (daltonisme, contraste) ; graphique à une teinte + lignes de seuil 3 et 4 (pas de couleur par valeur). Audit axe-core + clavier + zoom 200 % : 4 défauts corrigés.

### S11-7 Réécrire la requête seulement pour traduire
- Mesuré après les prompts multi-cours : anglais 18/20 (19/20 avant). Cause : test02, question anglaise réécrite par le routeur avec des mots perdus, page 279 manquée. Le routeur réécrivait 5 à 7 questions anglaises sur 25. Choix : si la langue de la question est celle du livre, on cherche avec les mots de l'étudiant (comme l'éval de recherche, hit@4 19/20) ; sinon la traduction. test02 vérifié seul : page 279 citée. Éval complète à relancer (quota gratuit épuisé).

## Étape 12 — Importer un manuel depuis l'interface

### S12-1 D6 changé à la demande : upload dans la Bibliothèque
- Demande explicite de Badr. Garde-fous gardés : case obligatoire « j'ai le droit d'utiliser ce document, sans données personnelles » (le texte part chez Gemini, offre gratuite), PDF vérifié (signature `%PDF-`, 100 Mo max), 150 pages étudiées au plus (temps CPU et quota), licence et auteurs demandés.

### S12-2 PDF envoyé tel quel, pas en multipart
- FastAPI a besoin de `python-multipart` pour les formulaires de fichiers (dépendance hors liste). Options : ajouter la dépendance, base64 dans du JSON (+33 %), ou le corps brut `application/pdf`. Choix : corps brut, puis un 2e appel JSON pour le formulaire. Le proxy Next.js transmet les octets tels quels.

### S12-3 Traitement en arrière-plan, un cours à la fois
- L'indexation (CPU) et le brouillon (Gemini) durent des minutes : tâche asyncio + `to_thread`, verrou pour un seul cours à la fois, état en mémoire (`queued`, `indexing`, `drafting`, `ready`, `failed`) interrogé toutes les 2 s. Après un redémarrage, l'état se déduit des notions. « Réessayer » ne réindexe pas si les passages sont déjà en base.

### S12-4 Cours importés hors de Git
- Registre `data/courses.local.json`, notions `data/notions/<id>.json`, PDF `data/raw/` : un document importé peut être privé, rien ne doit partir sur GitHub. Supprimer un cours efface ses passages, ses fichiers et son entrée (les notes Spring restent).

### S12-5 Deux défauts trouvés en vrai
- Le dernier chapitre du sommaire ne gardait qu'une page (fin = début) : il va maintenant jusqu'à la fin du livre. Les sections numérotées de résumé (« 5.6 Chapter summary ») donnaient une fausse notion : elles sont ignorées au brouillon (6 → 5 notions).

## Étape 13 — Démo publique sans appel LLM (plan v2, S1)

### S13-1 Réponses pré-calculées, servies par Next.js seul
- Options : héberger l'API avec Gemini (interdit en offre gratuite pour des utilisateurs EEE/UK, et la clé serait exposée au quota public), rejouer le cache LLM côté API (il faut encore FastAPI, la base et le modèle e5), ou figer des réponses. Choix : `scripts/build_demo.py` fait tourner le **vrai** agent une fois (11 questions, 3 quiz par langue et par cours, 3 explications Feynman) → `frontend/demo/data.json` (85 Ko). Avec `DEMO_MODE=1`, les routes `/api/*` et les pages serveur lisent ce fichier : aucun FastAPI, aucune base, aucune clé.

### S13-2 Notes dans un cookie, mêmes règles que Spring
- Les notes de la démo doivent rester chez le visiteur (rien à stocker côté serveur, pas de compte). Cookie `demo_scores` HttpOnly : cours → notion → 3 dernières notes (tout ce que la règle de maîtrise lit). Pire cas mesuré : 1 765 octets pour les 32 notions (limite des navigateurs : 4 096). Maîtrise, plan et notation du quiz portés en TypeScript avec les mêmes seuils (faible < 3, maîtrisé ≥ 4, arrondi au demi supérieur), testés.

### S13-3 « Aucune requête sortante » prouvé par un test qui peut échouer
- Vitest piège `fetch` et `net.Socket.prototype.connect` : toute connexion est notée et fait échouer le test. Un test témoin enlève `DEMO_MODE` et vérifie que le piège attrape bien l'appel du proxy vers l'API. Vérifié aussi en vrai : serveur Next lancé avec un mouchard de sockets, parcours complet dans Chromium → 0 connexion sortante, 0 requête du navigateur hors du site.

### S13-4 Vitest 5.0.3 + Vite 7.3.7, installés avec npm 11
- Vitest 5 exige Vite en pair. npm 10 plante (`Cannot read properties of null (reading 'edgesOut')`) en résolvant les pairs optionnels de Vite 8 (`@vitejs/devtools` → `vitest@*`). Choix : Vite 7.3.7 (sans ce pair), versions publiées depuis plus de 2 semaines, lockfile écrit par npm 11.20.0 ; `npm ci` de npm 10 l'accepte (vérifié), aucune version existante modifiée.

### S13-5 Lecteur de la démo : lien vers openstax.org
- Pas de PDF local dans la démo, et le PDF d'OpenStax n'autorise pas la lecture depuis un autre site (pas d'en-tête CORS, vérifié à l'étape 11) : react-pdf ne peut pas l'afficher. Plan B prévu à l’étape 8 : le passage cité est recopié, et un lien ouvre `pdf_url#page=N` dans un nouvel onglet.

## Étape 14 — Évaluation de régression en CI (plan v2, S4)

### S14-1 Réponses du LLM rejouées, pas appelées
- Options : appeler Gemini en CI (clé dans les secrets GitHub, quota consommé à chaque push, réponses qui varient), juge LLM, ou rejouer des réponses enregistrées. Choix : `LLM_OFFLINE=1` + `LLM_CACHE_DIR=eval/replay` (112 réponses versionnées, 24 Ko). La clé du cache reste sha256(modèle + prompt) : un prompt qui change n'a pas d'enregistrement et compte comme une réponse fausse. Toute modification de ce que voit le LLM doit donc être réenregistrée (`eval.regression record`) et repasser les seuils.

### S14-2 Modèle de base dans la porte
- Le modèle fine-tuné n'est pas sur le Hub (jeton HF absent) : la CI ne peut pas le charger. La porte utilise le modèle par défaut du code (`rag.embeddings.BASE_MODEL`, e5 de base public). Mesuré avec lui : EN 16/20, FR 18/20 réponses justes (fine-tuné : 18 et 19).

### S14-3 Seuils : la mesure moins une question
- hit@4 et MRR −0,05, réponses justes −1, pièges 5/5 sans marge (un piège accepté = une réponse inventée). La marge absorbe un rang inversé par le bruit des calculs flottants sur un autre processeur ; une vraie régression fait perdre plusieurs questions.

### S14-4 Régression volontaire choisie pour ce que les tests unitaires ne voient pas
- Morceaux de 100 tokens au lieu de 300, ou mauvais préfixe e5 : déjà attrapés par un test unitaire. Modèle anglais `all-MiniLM-L6-v2` par défaut : 173 tests unitaires verts, porte rouge (FR hit@4 0,75 → 0,60, MRR 0,604 → 0,514 ; EN MRR monte à 0,793). Seule l'éval bilingue le voit.

### S14-5 Observation non adoptée : chevauchement 0
- En cherchant une régression, `OVERLAP = 0` a donné EN 0,95 et FR 0,80 sur le jeu **test**. Non adopté : D3 réserve le jeu test à la mesure finale, un réglage se décide sur le jeu dev. À évaluer sur dev plus tard.

## Étape 15 — Répétition espacée FSRS (plan v2, S3)

### S15-1 FSRS calculé côté Python, rejoué depuis l'historique
- py-fsrs 6.3.2 (MIT, roue pure Python, seule dépendance `typing-extensions`) est en Python ; Spring garde les notes. Options : stocker l'état FSRS dans Spring (porter l'algorithme en Java), ou rejouer l'historique daté à chaque demande. Choix : Spring expose `GET /api/scores` (notes datées), FastAPI rejoue les notes de chaque notion dans l'ordre. Rien de plus à stocker, et l'état ne peut pas diverger des notes.

### S15-2 Réglages : jours, pas de hasard, pas de « Easy »
- `learning_steps=()` et `relearning_steps=()` : une notion se révise sur des jours, pas à 1 ou 10 minutes (réglages par défaut pensés pour des cartes). `enable_fuzzing=False` : mêmes notes = mêmes dates, donc tests à dates fixes. Note → évaluation : 0-2 Again, 3 Hard, 4-5 Good. Jamais Easy : c'est une auto-évaluation, et une seule bonne réponse à un QCM ne la justifie pas.

### S15-3 Question passée = aucune note
- `chosen_index` absent → question non notée ; si toutes les questions d'une notion sont passées, aucune note n'est envoyée à Spring, donc ni la maîtrise ni la date de révision ne bougent. Vérifié en vrai : 12 notes avant, 12 après.

### S15-4 Le quiz commence par les notions dues
- Ordre : notions dues aujourd'hui ou en retard (FSRS), puis notions faibles (Spring), puis hasard. Démo publique : pas de FSRS (le cookie ne garde ni dates ni historique complet), la carte est masquée.

## Étape 16 — Quiz aux gestes et « Passer » (plan v2, S6)

### S16-1 Règle géométrique, indices vérifiés
- Indices pris dans l'énumération officielle `HandLandmark` du code source de MediaPipe (poignet 0, pointes 8/12/16/20, articulations du milieu 6/10/14/18) ; la page ai.google.dev n'est pas joignable d'ici. Doigt levé = pointe plus loin du poignet que l'articulation du milieu ; pouce ignoré. Testé sur les points produits par le vrai modèle sur 4 images d'exemple de Google (rapports 1,3-1,5 levé contre 0,34-0,81 plié) ; 3 et 4 doigts : mains synthétiques dérivées de « victoire », marquées comme telles.

### S16-2 Stabilisation : maintien, réarmement, annulation
- Même valeur 1 s (poing 1,5 s) ; un geste ne se déclenche qu'une fois puis doit changer (sinon une main immobile répondrait à toutes les questions) ; main retirée ou Échap = annulation. Après la correction, main ouverte = question suivante. Le geste appelle les mêmes fonctions que le clavier (`choose`, `skip`, `next`).

### S16-3 Fichiers de MediaPipe : WASM chez nous, modèle chez Google, télémétrie bloquée
- WASM copié depuis `node_modules` dans `public/mediapipe` avant `dev` et `build` (pas de CDN, version alignée sur le JS, hors Git) ; le modèle (7,8 Mo) vient de l'URL versionnée officielle, téléchargé seulement si la caméra est activée (pas de modèle dans Git). Test réel : MediaPipe 1.1.0 envoie des statistiques d'usage à `odml.pa.googleapis.com` sans option pour les couper. Choix : en-tête CSP `connect-src 'self' https://storage.googleapis.com` sur tout le site ; vérifié : requête refusée par le navigateur, gestes, PDF et démo intacts.

### S16-4 Question passée : statut dans Spring, aucune note
- Table `quiz_answer` (statut CORRECT / INCORRECT / SKIPPED) alimentée par FastAPI à chaque quiz ; les notes restent dans `scores`. Une question passée n'est pas notée : ni maîtrise ni FSRS ne bougent ; le résumé la liste avec la page à relire. Ce journal servira au trophée « Sans faute » (étape 18).

## Étape 17 — Comptes : Spring Security et JWT (plan v2, S2)

### S17-1 Spring signe et vérifie, les autres relaient
- Spring est le service métier : il stocke les comptes (BCrypt) et signe le JWT (HS256, `NimbusJwtEncoder` du starter `spring-boot-starter-security-oauth2-resource-server`, API vérifiée dans la version 7.1.1). Next.js range le jeton dans un cookie HttpOnly et l'envoie en `Authorization` à FastAPI, qui le relaie tel quel ; FastAPI ne vérifie rien lui-même. Une seule clé (`JWT_SECRET`), dans Spring seulement ; démarrage refusé si elle fait moins de 32 caractères.

### S17-2 Identité tirée du jeton, jamais de la requête
- L'identifiant utilisateur est le `sub` du jeton vérifié : aucune route ne prend un `userId` en paramètre, sauf `GET /api/users/{id}`, qui renvoie 403 si l'id n'est pas celui du jeton. Sans jeton : 401 (filtre du serveur de ressources). Même 401 pour un e-mail inconnu ou un mauvais mot de passe.

### S17-3 Cookie HttpOnly plutôt que localStorage
- Un script injecté ne peut pas lire un cookie HttpOnly ; `SameSite=Lax` limite les envois depuis d'autres sites, `Secure` en HTTPS. Le proxy renvoie seulement l'e-mail à la page, jamais le jeton. Le nom affiché vient du jeton décodé côté serveur, pour l'affichage seulement.

### S17-4 Anciennes lignes sans utilisateur
- Vécu : Hibernate (`ddl-auto=update`) ne peut pas ajouter une colonne `user_id NOT NULL` à une table qui contient déjà des lignes ; la colonne manquait et l'enregistrement du quiz renvoyait 500. Choix : `user_id` nullable dans `scores` et `quiz_answer` ; les lignes d'avant les comptes restent en base mais ne sont visibles par personne.
