# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Dict, Optional

import msgpack

from swh.counters.journal_client import (
    process_journal_messages,
    process_releases,
    process_revisions,
)
from swh.counters.redis import Redis
from swh.model.hashutil import hash_to_bytes
from swh.model.model import (
    ObjectType,
    Person,
    Release,
    Revision,
    RevisionType,
    Timestamp,
    TimestampWithTimezone,
)

DATE = TimestampWithTimezone(
    timestamp=Timestamp(seconds=0, microseconds=0), offset=0, negative_utc=False
)


def _create_release(author_fullname: Optional[str]) -> Dict:
    """Use Release.to_dict to be sure the field's name used to retrieve
       the author is correct"""

    author = None
    if author_fullname:
        author = Person(fullname=bytes(author_fullname, "utf-8"), name=None, email=None)

    release = Release(
        name=b"Release",
        message=b"Message",
        target=hash_to_bytes("34973274ccef6ab4dfaaf86599792fa9c3fe4689"),
        target_type=ObjectType.CONTENT,
        synthetic=True,
        author=author,
    )

    return release.to_dict()


def _create_revision(author_fullname: str, committer_fullname: str) -> Dict:
    """Use Revision.to_dict to be sure the names of the fields used to retrieve
       the author and the committer are correct"""
    revision = Revision(
        committer_date=DATE,
        date=None,
        type=RevisionType.GIT,
        parents=(),
        directory=hash_to_bytes("34973274ccef6ab4dfaaf86599792fa9c3fe4689"),
        synthetic=True,
        message=None,
        author=Person(fullname=bytes(author_fullname, "utf-8"), name=None, email=None),
        committer=Person(
            fullname=bytes(committer_fullname, "utf-8"), name=None, email=None
        ),
    )

    return revision.to_dict()


RELEASES = {
    rel["id"]: msgpack.dumps(rel)
    for rel in [
        _create_release(author_fullname="author 1"),
        _create_release(author_fullname="author 2"),
        _create_release(author_fullname=None),
    ]
}


RELEASES_AUTHOR_FULLNAMES = {b"author 1", b"author 2"}


REVISIONS = {
    rev["id"]: msgpack.dumps(rev)
    for rev in [
        _create_revision(author_fullname="author 1", committer_fullname="committer 1"),
        _create_revision(author_fullname="author 2", committer_fullname="committer 2"),
        _create_revision(author_fullname="author 2", committer_fullname="committer 1"),
        _create_revision(author_fullname="author 1", committer_fullname="committer 2"),
    ]
}


REVISIONS_AUTHOR_FULLNAMES = {b"author 1", b"author 2"}
REVISIONS_COMMITTER_FULLNAMES = {b"committer 1", b"committer 2"}
REVISIONS_PERSON_FULLNAMES = REVISIONS_AUTHOR_FULLNAMES | REVISIONS_COMMITTER_FULLNAMES


def test_journal_client_all_keys(local_redis_host):
    redis = Redis(host=local_redis_host)

    keys = {
        "coll1": {b"key1": b"value1", b"key2": b"value2"},
        "coll2": {b"key3": b"value3", b"key4": b"value4", b"key5": b"value5"},
    }

    process_journal_messages(messages=keys, counters=redis)

    assert redis.get_counts(redis.get_counters()) == {b"coll1": 2, b"coll2": 3}


def test_journal_client_process_revisions(local_redis_host):
    redis = Redis(host=local_redis_host)

    process_revisions(REVISIONS, redis)

    assert redis.get_counts(redis.get_counters()) == {
        b"person": len(REVISIONS_PERSON_FULLNAMES)
    }


def test_journal_client_process_releases(local_redis_host):
    redis = Redis(host=local_redis_host)

    process_releases(RELEASES, redis)

    assert redis.get_counts(redis.get_counters()) == {
        b"person": len(RELEASES_AUTHOR_FULLNAMES)
    }


def test_journal_client_process_releases_without_authors(local_redis_host):
    releases = {
        rel["id"]: msgpack.dumps(rel)
        for rel in [
            _create_release(author_fullname=None),
            _create_release(author_fullname=None),
        ]
    }

    redis = Redis(host=local_redis_host)

    process_releases(releases, redis)

    assert redis.get_counts(redis.get_counters()) == {}
