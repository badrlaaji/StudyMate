# Journal

Format : 3 lignes par étape (fait, bloqué, chiffres mesurés).

## Étape 0 — Repo et environnement (2026-10-20)
- **Fait** : venv uv Python 3.13 ; torch CPU (`cuda.is_available() = False`) ; e5 chargé avec préfixes ; Neon via asyncpg depuis Windows : `CREATE EXTENSION vector` OK, TLS obligatoire vérifié ; Gemini `gemini-3.5-flash-lite` → réponse Pydantic valide (`json_schema`, `thinking_level=minimal`) ; dépendances figées (wheels Windows cp313 vérifiées) ; tests verts.
- **Bloqué** : quota AI Studio à relever.
- **Chiffres** : Python 3.13.16 ; uv 0.13.3 (Windows) / 0.11.32 (Linux) ; torch 2.14.1+cpu ; 94 paquets runtime / 98 dev (132 au total) ; e5 : dim 384, cosinus 0,9066 (passage pertinent) vs 0,7730 (hors sujet) ; Neon : PostgreSQL 18.6 + pgvector 0.8.6 ; base locale/CI : PostgreSQL 17.10 + pgvector 0.8.2 ; `check_env all` en 42 s (Linux, modèle en cache) ; 8 tests passés.

### Quota Gemini (AI Studio → Rate limit, offre gratuite)
| Modèle | Requêtes/min | Requêtes/jour | Tokens/min | Relevé le |
| --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | [X] | [X] | [X] | [X] |
