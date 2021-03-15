# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import logging
import os
from typing import Any, Dict

from swh.core import config
from swh.core.api import RPCServerApp
from swh.counters import get_counters
from swh.counters.interface import CountersInterface

logger = logging.getLogger(__name__)

app = None


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

    app.add_url_rule("/", "index", index)

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
