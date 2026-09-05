import os

import pytest


@pytest.fixture
def test_base_url():
    return os.getenv(
        "TEST_BASE_URL",
        "http://127.0.0.1:8000"
    )
