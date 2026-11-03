# Architecture — Eco Sentinel Africa

```
Eco-sentinel-Africa/
├── src/eco_sentinel/
│   ├── api/              # FastAPI, worker, broadcast WS, dashboard.html
│   ├── config/           # Settings 12-factor (pydantic-settings, défaut meta)
│   ├── core/             # logging corrélé, meta_client (AsyncOpenAI Responses), exceptions
│   ├── ingestion/        # service queue bornée (WebSocket + sampling)
│   ├── vision/           # port + mock + sam31 (NMS, fallback Spark, filtre 0.45)
│   ├── events/           # detector (dedup 60s, persistance 1)
│   ├── orchestration/    # router Wonder (Meta Muse Wonder)
│   ├── agents/           # classification, geo, research, report (Meta Muse Spark)
│   ├── analysis/         # analysis (grille 0.78/0.90)
│   ├── alerts/           # moteur règles + dedup
│   ├── a2a/              # protocole A2A (AgentCard, bus)
│   ├── persistence/      # store in-memory (OrderedDict, async)
│   ├── security/         # validations
│   ├── observability/    # metrics (compteurs/latences)
│   ├── services/         # health + services métier
│   └── utils/            # helpers (slugify, etc.)
├── src/meta_ai_dev/      # shim compat — ré-exporte eco_sentinel (ne pas étendre)
├── tests/unit, tests/integration, evals/datasets/golden.jsonl
├── configs/app.example.yaml
├── Dockerfile            # builder → runtime, HEALTHCHECK /health
├── docker-compose.yml    # app + deepeval (profile eval)
├── .github/workflows/ci.yml
└── pyproject.toml        # source unique (eco_sentinel)
```

Principes : `src` layout, `.venv` local via `uv`, `pyproject.toml` unique source de vérité.

Nommage : tout le code métier vit sous `eco_sentinel.*`. `meta_ai_dev` n'est qu'un shim
de compatibilité qui ré-exporte `eco_sentinel` — ne pas y ajouter de code.
