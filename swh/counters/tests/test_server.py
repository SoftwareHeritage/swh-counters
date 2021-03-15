# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from typing import Any, Dict

import pytest
import yaml

from swh.core.api import RPCServerApp
from swh.counters.api import server
from swh.counters.api.server import load_and_check_config, make_app_from_configfile


def teardown_function():
    # Ensure there is no configuration loaded from a previous test
    server.api = None


@pytest.fixture
def swh_counters_server_config() -> Dict[str, Any]:
    return {"counters": {"cls": "redis", "hosts": "redis",}}


@pytest.fixture
def swh_counters_server_config_on_disk(
    tmp_path, monkeypatch, swh_counters_server_config
) -> str:
    return _environment_config_file(tmp_path, monkeypatch, swh_counters_server_config)


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
