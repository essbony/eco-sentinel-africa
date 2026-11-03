"""Exemple officiel Meta Dev AI — inférence Muse via OpenAI client (même base_url/api).

Source : doc Meta — tous les modèles Muse partagent le même BASE_URL et la même API.
    import os
    from openai import OpenAI
    client = OpenAI(
        base_url="https://api.meta.ai/v1",
        api_key=os.environ["MODEL_API_KEY"],
    )
    response = client.responses.create(
        model="muse-spark-1.3",
        input="What is the capital of France?",
    )
    print(response.model_dump_json(indent=2))

Ce fichier montre la version sync (doc) et la version async utilisée par le pipeline
Eco Sentinel (AsyncOpenAI — même base_url/api_key).
"""

import os

# --- 1) Sync — exemple exact de la doc (recommandé pour scripts / one-shot) ---
from openai import OpenAI

client = OpenAI(
    base_url="https://api.meta.ai/v1",
    api_key=os.environ.get("MODEL_API_KEY", ""),
)

# Décommente pour tester en live (nécessite MODEL_API_KEY) :
# response = client.responses.create(
#     model="muse-spark-1.3",
#     input="What is the capital of France?",
# )
# print(response.model_dump_json(indent=2))

# --- 2) Via le helper du projet (même base_url/api_key, mais avec Settings + fallback) ---
# from eco_sentinel.core.meta_client import get_sync_client
# sync_client = get_sync_client()
# if sync_client:
#     resp = sync_client.responses.create(  # noqa: E501
#         model="muse-spark-1.3", input="What is the capital of France?"
#     )
#     print(resp.model_dump_json(indent=2))

# --- 3) Async — version utilisée par le pipeline (agents, vision, router) ---
# import asyncio
# from eco_sentinel.core.meta_client import get_meta_client
# async def main():
#     mclient = get_meta_client()  # AsyncOpenAI(base_url, api_key)
#     resp = await mclient.responses.create(model="muse-spark-1.3", input="Hello")
#     print(resp.model_dump_json(indent=2))
# asyncio.run(main())

# --- 4) Helper générique du projet (Responses + fallback chat.completions) ---
# from eco_sentinel.core.meta_client import call_meta_responses
# import asyncio
# text = asyncio.run(  # noqa: E501
#     call_meta_responses(model="muse-spark-1.3", input_text="What is the capital of France?")
# )
# print(text)
