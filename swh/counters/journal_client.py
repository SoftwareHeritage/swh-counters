# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, Iterable

from swh.counters.redis import Redis


def process_journal_messages(
    messages: Dict[str, Iterable[Any]], *, counters: Redis
) -> None:
    """Worker function for `JournalClient.process(worker_fn)`"""

    for key in messages.keys():
        counters.add(key, messages[key])
