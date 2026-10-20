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
