# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.counters.journal_client import process_journal_messages
from swh.counters.redis import Redis


def test__journal_client__all_keys(mocker):

    mock = mocker.patch("swh.counters.redis.Redis.add")

    redis = Redis(host="localhost")

    keys = {"coll1": [b"key1", b"key2"], "coll2": [b"key3", b"key4", b"key5"]}

    process_journal_messages(messages=keys, counters=redis)

    assert mock.call_count == 2

    first_call_args = mock.call_args_list[0]
    assert first_call_args[0][0] == "coll1"
    assert first_call_args[0][1] == keys["coll1"]

    second_call_args = mock.call_args_list[1]
    assert second_call_args[0][0] == "coll2"
    assert second_call_args[0][1] == keys["coll2"]
