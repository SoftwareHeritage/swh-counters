# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import os
from typing import List

import pytest

from swh.counters.history import History

TEST_HISTORY_CONFIG = {
    "prometheus_host": "prometheus",
    "prometheus_port": 8888,
    "prometheus_collection": "swh.collection",
    "cache_base_directory": "/tmp",
    "live_data_start": "10",
    "interval": "20h",
    "query_range_uri": "/my/uri",
    "labels": {"label1": "value1", "label2": "value2"},
}

TEST_JSON = {"key1": "value1", "key2": "value2"}
CACHED_DATA = {"content": [[10, 1.5], [12, 2.0]], "revision": [[11, 4], [13, 5]]}


@pytest.fixture
def history():
    return History(**TEST_HISTORY_CONFIG)


def test_history_compute_url(history):

    end = 99
    object_type = "content"

    url = history._compute_url(object=object_type, end=end,)

    assert url == (
        f'http://{TEST_HISTORY_CONFIG["prometheus_host"]}:'
        f'{TEST_HISTORY_CONFIG["prometheus_port"]}/'
        f'{TEST_HISTORY_CONFIG["query_range_uri"]}?'
        f'query=sum({TEST_HISTORY_CONFIG["prometheus_collection"]}'
        f'{{label1="value1",label2="value2",'
        f'object_type="{object_type}"}})&'
        f'start={TEST_HISTORY_CONFIG["live_data_start"]}&end={end}'
        f'&step={TEST_HISTORY_CONFIG["interval"]}'
    )


@pytest.mark.parametrize(
    "source, expected", [([1, "10"], [1000, 10.0]), ([2, "10.1"], [2000, 10.1]),]
)
def test_history__adapt_format(history, source, expected):
    result = history._adapt_format(source)

    assert expected == result


def test_history__validate_filename(history):
    with pytest.raises(ValueError, match="path information"):
        history._validate_filename("/test.json")

    with pytest.raises(ValueError, match="path information"):
        history._validate_filename("../../test.json")

    history._validate_filename("test.json")


def test_history_get_history(history, tmp_path):
    history.cache_base_directory = tmp_path

    json_file = "test.json"
    full_path = f"{tmp_path}/{json_file}"

    with open(full_path, "w") as f:
        f.write(json.dumps(TEST_JSON))

    result = history.get_history(json_file)
    assert result == TEST_JSON


def test_history_get_history_relative_path_failed(history):
    with pytest.raises(ValueError, match="path information"):
        history.get_history("/test.json")


def test_history__get_timestamp_history(history, requests_mock, datadir, mocker):
    object = "content"
    end = 100
    url = history._compute_url(object, end)

    mock = mocker.patch("time.time")
    mock.return_value = end

    request_content_file = os.path.join(datadir, "content.json")
    with open(request_content_file, "r") as f:
        content = f.read()

    requests_mock.get(
        url, [{"content": bytes(content, "utf-8"), "status_code": 200},],
    )

    result = history._get_timestamp_history(object)

    assert result == [[100000, 10.0], [100000, 20.0], [110000, 30.0]]


def test_history__get_timestamp_history_request_failed(
    history, requests_mock, datadir, mocker
):
    object = "content"
    end = 100
    url = history._compute_url(object, end)

    mock = mocker.patch("time.time")
    mock.return_value = end

    requests_mock.get(
        url, [{"content": None, "status_code": 503},],
    )

    result = history._get_timestamp_history(object)

    assert result == []


def _configure_request_mock(
    history_object, mock, datadir, objects: List[str], end: int
):
    for object_type in objects:
        url = history_object._compute_url(object_type, end)
        request_content_file = os.path.join(datadir, f"{object_type}.json")
        with open(request_content_file, "r") as f:
            content = f.read()
        mock.get(
            url, [{"content": bytes(content, "utf-8"), "status_code": 200},],
        )


def test_history__refresh_history_with_static_data(
    history, requests_mock, mocker, datadir, tmp_path
):
    """Test the generation of a cache file with an aggregation
       of static data and live data from prometheus
    """
    objects = ["content", "revision"]
    static_file_name = "static.json"
    cache_file = "result.json"
    end = 100

    with open(f"{tmp_path}/{static_file_name}", "w") as f:
        f.write(json.dumps(CACHED_DATA))

    _configure_request_mock(history, requests_mock, datadir, objects, end)

    mock = mocker.patch("time.time")
    mock.return_value = end

    history.cache_base_directory = tmp_path

    history.refresh_history(
        cache_file=cache_file, objects=objects, static_file=static_file_name
    )

    result_file = f"{tmp_path}/{cache_file}"
    assert os.path.isfile(result_file)

    expected_history = {
        "content": [
            [10, 1.5],
            [12, 2.0],
            [100000, 10.0],
            [100000, 20.0],
            [110000, 30.0],
        ],
        "revision": [[11, 4], [13, 5], [80000, 1.0], [90000, 2.0], [95000, 5.0]],
    }

    with open(result_file, "r") as f:
        content = json.load(f)

    assert expected_history == content


def test_history__refresh_history_without_historical(
    history, requests_mock, mocker, datadir, tmp_path
):
    """Test the generation of a cache file with only
       live data from prometheus"""
    objects = ["content", "revision"]
    cache_file = "result.json"
    end = 100

    _configure_request_mock(history, requests_mock, datadir, objects, end)

    mock = mocker.patch("time.time")
    mock.return_value = end

    history.cache_base_directory = tmp_path

    history.refresh_history(cache_file=cache_file, objects=objects)

    result_file = f"{tmp_path}/{cache_file}"
    assert os.path.isfile(result_file)

    expected_history = {
        "content": [[100000, 10.0], [100000, 20.0], [110000, 30.0]],
        "revision": [[80000, 1.0], [90000, 2.0], [95000, 5.0]],
    }

    with open(result_file, "r") as f:
        content = json.load(f)

    assert expected_history == content
