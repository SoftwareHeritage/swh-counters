# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from typing import Any, Dict, List

from confluent_kafka import KafkaError

from swh.journal.client import JournalClient, _error_cb


class KeyOrientedJournalClient(JournalClient):
    """Journal Client implementation which only uses the message keys.
       This does not need to bother with the message deserialization (contrary
       to `swh.journal.client.JournalClient`)
    """

    def handle_messages(self, messages, worker_fn):
        keys: Dict[str, List[Any]] = defaultdict(list)
        nb_processed = 0

        for message in messages:
            error = message.error()
            if error is not None:
                if error.code() == KafkaError._PARTITION_EOF:
                    self.eof_reached.add((message.topic(), message.partition()))
                else:
                    _error_cb(error)
                continue
            if message.value() is None:
                # ignore message with no payload, these can be generated in tests
                continue
            nb_processed += 1
            object_type = message.topic().split(".")[-1]
            keys[object_type].append(message.key())

        if keys:
            worker_fn(dict(keys))
            self.consumer.commit()

        at_eof = self.stop_on_eof and all(
            (tp.topic, tp.partition) in self.eof_reached
            for tp in self.consumer.assignment()
        )

        return nb_processed, at_eof
