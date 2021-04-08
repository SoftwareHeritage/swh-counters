# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import json
import re
from typing import Any, Dict

import pytest
from redis import Redis as RedisClient
import yaml

from swh.core.api import RPCServerApp
from swh.counters.api import server
from swh.counters.api.server import load_and_check_config, make_app_from_configfile


def teardown_function():
    # Ensure there is no configuration loaded from a previous test
    server.app = None


@pytest.fixture
def swh_counters_server_config() -> Dict[str, Any]:
    return {"counters": {"cls": "redis", "host": "redis",}}


@pytest.fixture
def swh_counters_server_config_on_disk(
    tmp_path, monkeypatch, swh_counters_server_config
) -> str:
    return _environment_config_file(tmp_path, monkeypatch, swh_counters_server_config)


@pytest.fixture
def history_test_client(tmp_path, monkeypatch):
    cfg = {
        "counters": {"cls": "redis", "host": "redis:6379"},
        "history": {
            "cls": "prometheus",
            "prometheus_host": "prometheus",
            "prometheus_port": "9090",
            "live_data_start": "0",
            "cache_base_directory": "/tmp",
        },
    }
    _environment_config_file(tmp_path, monkeypatch, cfg)

    app = make_app_from_configfile()
    app.config["TESTING"] = True
    return app.test_client()


def write_config_file(tmpdir, config_dict: Dict, name: str = "config.yml") -> str:
    """Prepare configuration file in `$tmpdir/name` with content `content`.

    Args:
        tmpdir (LocalPath): root directory
        content: Content of the file either as string or as a dict.
                            If a dict, converts the dict into a yaml string.
        name: configuration filename

    Returns
        path of the configuration file prepared.

    """
    config_path = tmpdir / name
    config_path.write_text(yaml.dump(config_dict), encoding="utf-8")
    # pytest on python3.5 does not support LocalPath manipulation, so
    # convert path to string
    return str(config_path)


def _environment_config_file(tmp_path, monkeypatch, content):
    conf_path = write_config_file(tmp_path, content)
    monkeypatch.setenv("SWH_CONFIG_FILENAME", conf_path)


@pytest.mark.parametrize("config_file", [None, ""])
def test_load_and_check_config_no_configuration(config_file):
    """Inexistent configuration files raises"""
    with pytest.raises(EnvironmentError, match="Configuration file must be defined"):
        load_and_check_config(config_file)


def test_load_and_check_config_inexistent_file():
    config_path = "/some/inexistent/config.yml"
    expected_error = f"Configuration file {config_path} does not exist"
    with pytest.raises(EnvironmentError, match=expected_error):
        load_and_check_config(config_path)


def test_load_and_check_config_wrong_configuration(tmpdir):
    """Wrong configuration raises"""
    config_path = write_config_file(tmpdir, {"something": "useless"})
    with pytest.raises(KeyError, match="Missing 'counters' configuration"):
        load_and_check_config(config_path)


def test_server_make_app_from_config_file(swh_counters_server_config_on_disk):
    app = make_app_from_configfile()

    assert app is not None
    assert isinstance(app, RPCServerApp)

    app2 = make_app_from_configfile()
    assert app is app2


def test_server_index(swh_counters_server_config_on_disk, mocker):
    """Test the result of the main page"""

    app = make_app_from_configfile()
    app.config["TESTING"] = True
    tc = app.test_client()

    r = tc.get("/")

    assert 200 == r.status_code
    assert b"SWH Counters" in r.get_data()


def test_server_metrics(local_redis, tmp_path, monkeypatch):
    """Test the metrics generation"""

    rc = RedisClient(host=local_redis.host, port=local_redis.port)
    data = {
        "col1": 1,
        "col2": 4,
        "col3": 6,
        "col4": 10,
    }

    for coll in data.keys():
        for i in range(0, data[coll]):
            rc.pfadd(coll, i)

    cfg = {
        "counters": {"cls": "redis", "host": f"{local_redis.host}:{local_redis.port}"}
    }
    _environment_config_file(tmp_path, monkeypatch, cfg)

    app = make_app_from_configfile()
    app.config["TESTING"] = True
    tc = app.test_client()

    r = tc.get("/metrics")

    assert 200 == r.status_code

    response = r.get_data().decode("utf-8")

    assert "HELP" in response
    assert "TYPE" in response

    for collection in data.keys():
        obj_type = f'object_type="{collection}"'
        assert obj_type in response

        pattern = r'swh_archive_object_total{col="value", object_type="%s"} (\d+)' % (
            collection
        )
        m = re.search(pattern, response)
        assert data[collection] == int(m.group(1))


def test_server_counters_history(history_test_client, mocker):
    """Test the counters history file download"""

    expected_result = {"content": [[1, 1], [2, 2]]}
    mock = mocker.patch("swh.counters.history.History.get_history")
    mock.return_value = expected_result

    r = history_test_client.get("/counters_history/test.json")

    assert 200 == r.status_code

    response = r.get_data().decode("utf-8")
    response_json = json.loads(response)

    assert response_json == expected_result
    assert "application/json" == r.headers["Content-Type"]


def test_server_counters_history_file_not_found(history_test_client, mocker):
    """ensure a 404 is returned when the file doesn't exists"""

    mock = mocker.patch("swh.counters.history.History.get_history")
    mock.side_effect = FileNotFoundError

    r = history_test_client.get("/counters_history/fake.json")

    assert 404 == r.status_code
