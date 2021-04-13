# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, Iterable, List

from swh.core.api import remote_api_endpoint


class CountersInterface:
    @remote_api_endpoint("check")
    def check(self):
        """Dedicated method to execute some specific check per implementation.
        """
        ...

    @remote_api_endpoint("add")
    def add(self, collection: str, keys: Iterable[Any]) -> None:
        """Add the provided keys to the collection
           Only count new keys.
        """
        ...

    @remote_api_endpoint("count")
    def get_count(self, collection: str) -> int:
        """Return the number of keys for the provided collection"""
        ...

    @remote_api_endpoint("counts")
    def get_counts(self, collections: List[str]) -> Dict[str, int]:
        """Return the number of keys for the provided collection"""
        ...

    @remote_api_endpoint("counters")
    def get_counters(self) -> Iterable[str]:
        """Return the list of managed counters"""
        ...


class HistoryInterface:
    @remote_api_endpoint("history")
    def get_history(self, cache_file: str):
        """Return the content of an history file previously created
           by the refresh_counters method"""

    @remote_api_endpoint("refresh_history")
    def refresh_history(self, cache_file: str):
        """Refresh the cache file containing the counters historical data.
           It can be an aggregate of live data and static data stored on
           a separate file"""
        ...
