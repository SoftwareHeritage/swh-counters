# Copyright (C) 2021 The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import inspect

import pytest

from swh.counters import get_counters, get_history
from swh.counters.api.client import RemoteCounters
from swh.counters.history import History
from swh.counters.in_memory import InMemory
from swh.counters.interface import CountersInterface
from swh.counters.redis import Redis

COUNTERS_IMPLEMENTATIONS = [
    ("remote", RemoteCounters, {"url": "localhost"}),
    ("redis", Redis, {"host": "localhost"}),
    ("memory", InMemory, {}),
]


def test_get_counters_failure():
    with pytest.raises(ValueError, match="Unknown counters class"):
        get_counters("unknown-counters")


@pytest.mark.parametrize("class_,expected_class,kwargs", COUNTERS_IMPLEMENTATIONS)
def test_get_counters(mocker, class_, expected_class, kwargs):
    if kwargs:
        concrete_counters = get_counters(class_, **kwargs)
    else:
        concrete_counters = get_counters(class_)
    assert isinstance(concrete_counters, expected_class)


@pytest.mark.parametrize("class_,expected_class,kwargs", COUNTERS_IMPLEMENTATIONS)
def test_types(mocker, class_, expected_class, kwargs):
    """Checks all methods of CountersInterface are implemented by this
    backend, and that they have the same signature.

    """
    # mocker.patch("swh.counters.redis.Redis")
    if kwargs:
        concrete_counters = get_counters(class_, **kwargs)
    else:
        concrete_counters = get_counters(class_)

    # Create an instance of the protocol (which cannot be instantiated
    # directly, so this creates a subclass, then instantiates it)
    interface = type("_", (CountersInterface,), {})()

    for meth_name in dir(interface):
        if meth_name.startswith("_"):
            continue
        interface_meth = getattr(interface, meth_name)

        missing_methods = []

        try:
            concrete_meth = getattr(concrete_counters, meth_name)
        except AttributeError:
            if not getattr(interface_meth, "deprecated_endpoint", False):
                # The backend is missing a (non-deprecated) endpoint
                missing_methods.append(meth_name)
                continue

        expected_signature = inspect.signature(interface_meth)
        actual_signature = inspect.signature(concrete_meth)

        assert expected_signature == actual_signature, meth_name

        assert missing_methods == []


def test_get_history_failure():
    with pytest.raises(ValueError, match="Unknown history class"):
        get_history("unknown-history")


def test_get_history():
    concrete_history = get_history(
        "prometheus",
        **{
            "prometheus_host": "",
            "prometheus_port": "",
            "live_data_start": "",
            "cache_base_directory": "",
        },
    )
    assert isinstance(concrete_history, History)
