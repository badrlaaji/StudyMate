# Journal

Format : 3 lignes par étape (fait, bloqué, chiffres mesurés).

## Étape 0 — Repo et environnement (2026-10-20)
- **Fait** : venv uv Python 3.13 ; dépendances figées (wheels Windows cp313 vérifiées) ; Gemini `gemini-3.5-flash-lite` → réponse Pydantic valide (`json_schema`, `thinking_level=minimal`) ; asyncpg + `CREATE EXTENSION vector` OK sur une base pgvector locale ; tests verts.
- **Bloqué** : torch CPU et e5 (index PyTorch et Hugging Face non autorisés par le réseau de l'environnement Linux) ; Neon injoignable depuis cet environnement (pas de DNS) → à vérifier sous Windows ; quota AI Studio à relever.
- **Chiffres** : Python 3.13.16, uv 0.11.32 ; 94 paquets runtime / 98 dev ; torch 2.14.1 (wheel Windows 124 Mo) ; PostgreSQL 17.10 + pgvector 0.8.2 (local) ; 8 tests passés.

### Quota Gemini (AI Studio → Rate limit, offre gratuite)
| Modèle | Requêtes/min | Requêtes/jour | Tokens/min | Relevé le |
| --- | --- | --- | --- | --- |
| gemini-3.5-flash-lite | [X] | [X] | [X] | [X] |
