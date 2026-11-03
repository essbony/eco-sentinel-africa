"""Fixtures partagées — Eco Sentinel Africa."""

import pytest  # noqa: E402

from eco_sentinel.config.settings import get_settings  # noqa: E402


@pytest.fixture()
def settings():
    return get_settings()
