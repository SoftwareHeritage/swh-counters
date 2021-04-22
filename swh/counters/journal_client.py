# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict, Iterable

from swh.counters.redis import Redis


def process_journal_messages_by_keys(
    messages: Dict[str, Iterable[Any]], *, counters: Redis
) -> None:
    """Count the number of different keys for a given message type"""

    for key in messages.keys():
        counters.add(key, messages[key])


def process_journal_messages(
    messages: Dict[str, Iterable[Any]], *, counters: Redis
) -> None:
    """Count the number of different values of an object's property.
       It allow for example to count the persons inside the
       Release (authors) and Revision (authors and committers) classes
    """

    if "revision" in messages:
        process_revisions(messages["revision"], counters)

    if "release" in messages:
        process_releases(messages["release"], counters)


def process_revisions(revisions: Iterable[Dict], counters: Redis):
    """Count the number of different authors and committers on the
       revisions (in the person collection)"""
    persons = set()
    for revision in revisions:
        persons.add(revision["author"]["fullname"])
        persons.add(revision["committer"]["fullname"])

    counters.add("person", list(persons))


def process_releases(releases: Iterable[Dict], counters: Redis):
    """Count the number of different authors on the
       releases (in the person collection)"""
    persons = set()
    for release in releases:
        author = release.get("author")
        if author and "fullname" in author:
            persons.add(author["fullname"])

    counters.add("person", list(persons))
