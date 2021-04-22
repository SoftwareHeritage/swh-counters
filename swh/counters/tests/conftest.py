# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging

import pytest
from redis import Redis as RedisClient

logger = logging.getLogger(__name__)


JOURNAL_OBJECTS_CONFIG_TEMPLATE = """
journal:
    brokers:
        - {broker}
    prefix: {prefix}
    group_id: {group_id}
"""


@pytest.fixture
def journal_config(kafka_server, kafka_prefix) -> str:
    return JOURNAL_OBJECTS_CONFIG_TEMPLATE.format(
        broker=kafka_server, group_id="test-consumer", prefix=kafka_prefix
    )


@pytest.fixture
def local_redis(redis_proc):
    yield redis_proc
    # Cleanup redis between 2 tests
    rc = RedisClient(host=redis_proc.host, port=redis_proc.port)
    rc.flushall()


@pytest.fixture
def local_redis_host(local_redis):
    return f"{local_redis.host}:{local_redis.port}"
