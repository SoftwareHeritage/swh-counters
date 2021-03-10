# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Iterable


class Redis:
    def __init__(self, host: str):
        pass

    def check(self):
        pass

    def add(self, collection: str, keys: Iterable[Any]) -> None:
        pass

    def get_count(self, collection: str) -> int:
        pass
