# Copyright (C) 2021-2026  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from typing import Dict

import msgpack

from swh.counters.interface import CountersInterface
from swh.journal.client import JournalClientBase


def process_journal_messages(
    messages: Dict[str, Dict[bytes, bytes]], counters: CountersInterface
) -> None:
    """Count the number of different values of an object's property.
    It allow for example to count the persons inside the
    Release (authors) and Revision (authors and committers) classes
    """
    for key in messages.keys():
        counters.add(key, messages[key])

    if "revision" in messages:
        process_revisions(messages["revision"], counters)

    if "release" in messages:
        process_releases(messages["release"], counters)


def process_revisions(revisions: Dict[bytes, bytes], counters: CountersInterface):
    """Count number of different authors/committers on revisions (in person collection)"""
    persons = set()
    for revision_bytes in revisions.values():
        revision = msgpack.loads(revision_bytes)
        persons.add(revision["author"]["fullname"])
        persons.add(revision["committer"]["fullname"])

    counters.add("person", list(persons))


def process_releases(releases: Dict[bytes, bytes], counters: CountersInterface):
    """Count number of different authors on the releases (in person collection)"""
    persons = set()
    for release_bytes in releases.values():
        release = msgpack.loads(release_bytes)
        author = release.get("author")
        if author and "fullname" in author:
            persons.add(author["fullname"])

    counters.add("person", list(persons))


class CountersJournalClient(JournalClientBase):
    """Journal Client implementation which only decodes the message keys. This does not
    need to bother with the message deserialization (contrary to
    :class:`swh.journal.client.JournalClientBase`).

    """

    def __init__(self, *args, **kwargs):
        self.counters = kwargs.pop("counters")
        super().__init__(*args, **kwargs)
        self._init_key_objects()

    def _init_key_objects(self) -> None:
        """(Re)Initialize the batch of decoded objects to commit."""
        self.key_objects: Dict[str, Dict[bytes, bytes]] = defaultdict(dict)

    def deserialize_message(self, message, object_type=None):
        # No need to deserialize the message since the main loop only counts the messages
        return message

    def process_one_object(self, decoded_object, decoded_object_type, raw_message):
        # The first argument is actually the non-decoded message so use directly the
        # raw_message to categorize message
        self.key_objects[decoded_object_type][raw_message.key()] = raw_message.value()

    def commit_batch(self):
        if self.key_objects:
            # Delegate the counting to previous implementations
            process_journal_messages(self.key_objects, self.counters)

        self._init_key_objects()
        # Commit the offsets
        super().commit_batch()
