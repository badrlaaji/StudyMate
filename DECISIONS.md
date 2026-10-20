# Décisions

Format : contexte, options, choix, pourquoi (5 lignes max par décision).

## Étape 0 — Repo et environnement

### S0-1 Paramètre SSL d'asyncpg pour Neon
- Contexte : Neon donne `?sslmode=require&channel_binding=require` (format libpq, prévu pour psycopg).
- Options : garder la chaîne telle quelle ; ou `?ssl=require` dans l'URL SQLAlchemy.
- Choix : `postgresql+asyncpg://…?ssl=require`, sans `channel_binding`. En asyncpg direct : `asyncpg.connect(dsn, ssl="require")`.
- Pourquoi (lu dans le code installé) : SQLAlchemy 2.1.5 passe chaque paramètre de l'URL à `asyncpg.connect()`, qui n'a pas d'argument `sslmode` ; asyncpg 0.32.0 envoie tout paramètre inconnu (`channel_binding`) au serveur comme réglage de session.

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

### S0-8 Configuration des outils sans `pyproject.toml`
- Choix : `pytest.ini` (`pythonpath = .`) et `ruff.toml`.
- Pourquoi : un `pyproject.toml` à la racine change le comportement de `uv run` (mode projet) ; on reste sur `requirements.txt` comme prévu (inférence).
