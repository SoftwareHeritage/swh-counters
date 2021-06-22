# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from collections import defaultdict
from typing import Dict
from urllib.parse import urlparse

import msgpack

from swh.counters.interface import CountersInterface


def process_journal_messages(
    messages: Dict[str, Dict[bytes, bytes]], *, counters: CountersInterface
) -> None:
    """Count the number of different values of an object's property.
       It allow for example to count the persons inside the
       Release (authors) and Revision (authors and committers) classes
    """
    for key in messages.keys():
        counters.add(key, messages[key])

    if "origin" in messages:
        process_origins(messages["origin"], counters)

    if "revision" in messages:
        process_revisions(messages["revision"], counters)

    if "release" in messages:
        process_releases(messages["release"], counters)


def process_origins(origins: Dict[bytes, bytes], counters: CountersInterface):
    """Count the number of different network locations in origin URLs."""
    origins_netloc = defaultdict(set)
    for origin_bytes in origins.values():
        origin = msgpack.loads(origin_bytes)
        parsed_url = urlparse(origin["url"])
        netloc = parsed_url.netloc
        if netloc.endswith("googlecode.com"):
            # special case for googlecode origins where URL netloc
            # has the form {account}.googlecode.com
            netloc = "googlecode.com"
        origins_netloc[f"origin_netloc:{netloc}"].add(origin["url"])

    for k, v in origins_netloc.items():
        counters.add(k, v)


def process_revisions(revisions: Dict[bytes, bytes], counters: CountersInterface):
    """Count the number of different authors and committers on the
       revisions (in the person collection)"""
    persons = set()
    for revision_bytes in revisions.values():
        revision = msgpack.loads(revision_bytes)
        persons.add(revision["author"]["fullname"])
        persons.add(revision["committer"]["fullname"])

    counters.add("person", list(persons))


def process_releases(releases: Dict[bytes, bytes], counters: CountersInterface):
    """Count the number of different authors on the
       releases (in the person collection)"""
    persons = set()
    for release_bytes in releases.values():
        release = msgpack.loads(release_bytes)
        author = release.get("author")
        if author and "fullname" in author:
            persons.add(author["fullname"])

    counters.add("person", list(persons))
