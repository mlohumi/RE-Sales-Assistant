import pytest

# This ensures Django is set up before tests run
pytest_plugins = [
    "django.contrib.auth",
]


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Automatically enable database access for all tests.

    This saves us from needing @pytest.mark.django_db on each test.
    """
    pass
