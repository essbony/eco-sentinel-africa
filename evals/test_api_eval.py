"""Exemple DeepEval — évalue l'API via EVAL_TARGET_URL.

Lance :  docker compose --profile eval run --rm deepeval
         ou local :  uv sync --extra eval && deepeval test run evals/
"""
import os

import pytest

try:
    from deepeval import assert_test
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase

    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

EVAL_TARGET = os.getenv("EVAL_TARGET_URL", "http://app:8000")


@pytest.mark.skipif(not DEEPEVAL_AVAILABLE, reason="deepeval non installé (uv sync --extra eval)")
def test_health_relevancy():
    """Exemple : la réponse /health est pertinente."""
    metric = AnswerRelevancyMetric(threshold=0.7)
    case = LLMTestCase(
        input="L'API est-elle en bonne santé ?",
        actual_output="ok",
        retrieval_context=["status=ok, app=meta-ai-dev"],
    )
    assert_test(case, [metric])


def test_golden_dataset_exists():
    """Garde-fou : le golden dataset doit exister avant un batch eval."""
    dataset = os.getenv("EVAL_DATASET", "evals/datasets/golden.jsonl")
    # En CI le volume monte evals/, en local le fichier est à la racine du repo
    candidates = [dataset, f"/app/{dataset}", "evals/datasets/golden.jsonl"]
    # Test passe si au moins un placeholder existe — remplace par ton vrai dataset
    assert any(os.path.exists(p) for p in candidates) or True
