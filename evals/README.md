# evals/

Suite DeepEval. `deepeval` est installé via l'extra `eval` (`deepeval>=2.2`).

## Datasets
- `datasets/golden.jsonl` — golden set minimal (remplace par tes traces prod).

## Lancer
```bash
# Local (hors Docker)
uv sync --extra eval
deepeval test run evals/ --verbose

# Dans Docker (attend que app soit healthy)
docker compose --profile eval run --rm deepeval
docker compose --profile eval run --rm deepeval deepeval test run evals/ --verbose

# CI batch (même commande, sortie JUnit/JSON dans evals/results/)
EVAL_RESULTS_DIR=/app/evals/results docker compose --profile eval run --rm deepeval
```

## Variables
Voir `.env.example` : `OPENAI_API_KEY` requis pour les métriques LLM (Meta API compatible).
`EVAL_TARGET_URL` pointe vers `http://app:8000` dans le compose (service `app`).
