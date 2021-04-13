# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import pytest
from redis import Redis as RedisClient

from swh.counters.redis import DEFAULT_REDIS_PORT, Redis


def test__redis__constructor():
    r = Redis("fakehost")
    assert r.host == "fakehost"
    assert r.port == DEFAULT_REDIS_PORT

    r = Redis("host:11")
    assert r.host == "host"
    assert r.port == 11

    with pytest.raises(ValueError, match="url"):
        Redis("fake:host:port")


def test__redis__only_one_client_instantiation(mocker):
    mock = mocker.patch("swh.counters.redis.RedisClient")

    r = Redis("redishost:1234")

    # ensure lazy loading
    assert r._redis_client is None

    client = r.redis_client

    assert mock.call_count == 1
    args = mock.call_args[1]
    assert args["host"] == "redishost"
    assert args["port"] == 1234
    assert r._redis_client is not None

    client2 = r.redis_client
    assert mock.call_count == 1
    assert client == client2


def test__redis__ping_ko():
    r = Redis("wronghost")
    assert r.check() is False


def test__redis__ping_ok(local_redis):
    r = Redis("%s:%d" % (local_redis.host, local_redis.port))
    assert r.check() is True


def test__redis__collection(local_redis):
    r = Redis("%s:%d" % (local_redis.host, local_redis.port))
    r.add("c1", [b"k1", b"k2", b"k3"])
    r.add("c2", [b"k1"])
    r.add("c3", [b"k2"])
    r.add("c3", [b"k5"])

    assert 3 == r.get_count("c1")
    assert 1 == r.get_count("c2")
    assert 2 == r.get_count("c3")
    assert 0 == r.get_count("c4")


def test__redis__collections(local_redis):
    client = RedisClient(host=local_redis.host, port=local_redis.port)
    client.pfadd("counter1", b"k1")
    client.pfadd("counter2", b"k2")

    r = Redis("%s:%d" % (local_redis.host, local_redis.port))

    counters = r.get_counters()

    assert 2 == len(counters)
    assert b"counter1" in counters
    assert b"counter2" in counters


def test__redis_counts(local_redis):
    client = RedisClient(host=local_redis.host, port=local_redis.port)
    client.pfadd("counter1", b"k1")
    client.pfadd("counter1", b"k2")
    client.pfadd("counter2", b"k1")
    client.pfadd("counter2", b"k2")
    client.pfadd("counter2", b"k3")
    client.pfadd("counter3", b"k3")

    r = Redis("%s:%d" % (local_redis.host, local_redis.port))

    counts = r.get_counts(["counter2", "counter1"])

    assert 2 == len(counts)
    assert 2 == counts["counter1"]
    assert 3 == counts["counter2"]
