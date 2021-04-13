# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import logging
from typing import Any, Dict, Iterable, List

from redis.client import Redis as RedisClient
from redis.exceptions import ConnectionError

DEFAULT_REDIS_PORT = 6379


logger = logging.getLogger(__name__)


class Redis:
    """Redis based implementation of the counters.
       It uses one HyperLogLog collection per counter"""

    _redis_client = None

    def __init__(self, host: str):
        host_port = host.split(":")

        if len(host_port) > 2:
            raise ValueError("Invalid server url `%s`" % host)

        self.host = host_port[0]
        self.port = int(host_port[1]) if len(host_port) > 1 else DEFAULT_REDIS_PORT

    @property
    def redis_client(self) -> RedisClient:

        if self._redis_client is None:
            self._redis_client = RedisClient(host=self.host, port=self.port)

        return self._redis_client

    def check(self):
        try:
            return self.redis_client.ping()
        except ConnectionError:
            logger.exception("Unable to connect to the redis server")
            return False

    def add(self, collection: str, keys: Iterable[Any]) -> None:
        redis = self.redis_client
        pipeline = redis.pipeline(transaction=False)

        [pipeline.pfadd(collection, key) for key in keys]

        pipeline.execute()

    def get_count(self, collection: str) -> int:
        return self.redis_client.pfcount(collection)

    def get_counts(self, collections: List[str]) -> Dict[str, int]:
        return {coll: self.get_count(coll) for coll in collections}

    def get_counters(self) -> Iterable[str]:
        return self.redis_client.keys()
