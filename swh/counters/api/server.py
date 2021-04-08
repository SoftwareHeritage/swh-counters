# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import logging
import os
from typing import Any, Dict, Optional

from flask import abort, jsonify

from swh.core import config
from swh.core.api import RPCServerApp
from swh.counters import get_counters, get_history
from swh.counters.interface import CountersInterface, HistoryInterface

logger = logging.getLogger(__name__)

app: Optional[RPCServerApp] = None


def make_app(config: Dict[str, Any]) -> RPCServerApp:
    """Initialize the remote api application.

    """
    app = RPCServerApp(
        __name__,
        backend_class=CountersInterface,
        backend_factory=lambda: get_counters(**config["counters"]),
    )

    handler = logging.StreamHandler()
    app.logger.addHandler(handler)

    app.config["counters"] = get_counters(**config["counters"])

    if "history" in config:
        app.add_backend_class(
            backend_class=HistoryInterface,
            backend_factory=lambda: get_history(**config["history"]),
        )
        app.config["history"] = get_history(**config["history"])
        app.add_url_rule(
            "/counters_history/<filename>", "history", get_history_file_content
        )

    app.add_url_rule("/", "index", index)
    app.add_url_rule("/metrics", "metrics", get_metrics)

    return app


def index():
    return "SWH Counters API server"


def load_and_check_config(config_file: str) -> Dict[str, Any]:
    """Check the minimal configuration is set to run the api or raise an
       error explanation.

    Args:
        config_file: Path to the configuration file to load
        type: configuration type. For 'local' type, more
                    checks are done.

    Raises:
        Error if the setup is not as expected

    Returns:
        configuration as a dict

    """
    if not config_file:
        raise EnvironmentError("Configuration file must be defined")

    if not os.path.exists(config_file):
        raise FileNotFoundError("Configuration file %s does not exist" % (config_file,))

    cfg = config.read(config_file)
    if "counters" not in cfg:
        raise KeyError("Missing 'counters' configuration")

    return cfg


def make_app_from_configfile():
    """Run the WSGI app from the webserver, loading the configuration from
       a configuration file.

       SWH_CONFIG_FILENAME environment variable defines the
       configuration path to load.

    """
    global app

    if app is None:
        config_file = os.environ.get("SWH_CONFIG_FILENAME")
        api_cfg = load_and_check_config(config_file)

        app = make_app(api_cfg)

    return app


def get_metrics():
    """expose the counters values in a prometheus format

        detailed format:
        # HELP swh_archive_object_total Software Heritage Archive object counters
        # TYPE swh_archive_object_total gauge
        swh_archive_object_total{col="value",object_type="<collection>"} <value>
        ...
    """

    response = [
        "# HELP swh_archive_object_total Software Heritage Archive object counters",
        "# TYPE swh_archive_object_total gauge",
    ]
    counters = app.config["counters"]

    for collection in counters.get_counters():
        collection_name = collection.decode("utf-8")
        value = counters.get_count(collection)
        line = 'swh_archive_object_total{col="value", object_type="%s"} %s' % (
            collection_name,
            value,
        )
        response.append(line)
    response.append("")

    return "\n".join(response)


def get_history_file_content(filename: str):
    assert app is not None
    try:
        content = app.config["history"].get_history(filename)
    except FileNotFoundError:
        abort(404)

    return jsonify(content)
