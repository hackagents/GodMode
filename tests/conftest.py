from __future__ import annotations

import os

import psycopg2
import pytest


def get_test_db_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL (or DATABASE_URL) to run database tests")
    return url


@pytest.fixture(scope="session")
def pg_url() -> str:
    return get_test_db_url()


@pytest.fixture
def pg_conn(pg_url):
    """A raw psycopg2 connection for fixture setup/teardown DDL."""
    conn = psycopg2.connect(pg_url)
    conn.autocommit = True
    yield conn
    conn.close()
