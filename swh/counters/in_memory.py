# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from typing import Any, Dict, Iterable, List


class InMemory:
    """InMemory implementation of the counters.
       Naive implementation using a Dict[str, Set]"""

    def __init__(self):
        self.counters = defaultdict(set)

    def check(self):
        return "OK"

    def add(self, collection: str, keys: Iterable[Any]) -> None:
        for value in keys:
            self.counters[collection].add(value)

    def get_count(self, collection: str) -> int:
        return len(self.counters.get(collection, []))

    def get_counts(self, collections: List[str]) -> Dict[str, int]:
        return {coll: self.get_count(coll) for coll in collections}

    def get_counters(self) -> Iterable[str]:
        return list(self.counters.keys())
