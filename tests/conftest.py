"""Fixtures partagées."""

import pytest  # noqa: E402

from meta_ai_dev.config.settings import get_settings  # noqa: E402


@pytest.fixture()
def settings():
    return get_settings()
