# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.counters.in_memory import InMemory


def test__inmemory__add():
    im = InMemory()

    im.add("counter1", ["val1"])
    im.add("counter2", ["val1"])
    im.add("counter1", [1])

    assert im.get_count("counter1") == 2
    assert im.get_count("counter2") == 1
    assert im.get_count("inexisting") == 0


def test__inmemory_getcounters():
    im = InMemory()

    assert len(im.get_counters()) == 0

    counters = ["c1", "c2", "c3"]

    count = 0

    for counter in counters:
        im.add(counter, [1, 2])
        count += 1
        assert count == len(im.get_counters())

    results = im.get_counters()
    assert results == counters


def test__inmemory_getcounts():
    im = InMemory()

    expected = {"c1": 1, "c2": 2, "c3": 0}

    im.add("c1", ["v1"])
    im.add("c2", ["v1", "v2"])

    result = im.get_counts(["c1", "c2", "c3"])
    assert result == expected


def test__inmemory_check():
    im = InMemory()

    assert im.check() == "OK"
