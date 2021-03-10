# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.core.api import RPCClient

from ..interface import CountersInterface


class RemoteCounters(RPCClient):
    """Proxy to a remote counters API"""

    backend_class = CountersInterface
