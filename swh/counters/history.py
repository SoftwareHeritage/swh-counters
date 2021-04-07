# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information
import json
import logging
import os
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class History:
    """Manage the historical data of the counters"""

    def __init__(
        self,
        prometheus_host: str,
        prometheus_port: int,
        live_data_start: int,
        cache_base_directory: str,
        interval: str = "12h",
        prometheus_collection: str = "swh_archive_object_total",
        query_range_uri="/api/v1/query_range",
        labels: Dict[str, str] = {},
    ):
        self.prometheus_host = prometheus_host
        self.prometheus_port = prometheus_port
        self.cache_base_directory = cache_base_directory
        self.live_data_start = live_data_start
        self.interval = interval
        self.prometheus_collection = prometheus_collection
        self.query_range_uri = query_range_uri
        self.labels = labels

    def _validate_filename(self, filename: str):
        if "/" in str(filename):
            raise ValueError("filename must not contain path information")

    def _compute_url(self, object: str, end: int,) -> str:
        """Compute the api url to request data from, specific to a label.

        Args:
            object: object_type/label data (ex: content, revision, ...)
            end: retrieve the data until this date (timestamp)

        Returns:
            The api url to fetch the label's data
        """
        labels = self.labels.copy()
        labels["object_type"] = object
        formated_labels = ",".join([f'{k}="{v}"' for k, v in labels.items()])

        url = (
            f"http://{self.prometheus_host}:{self.prometheus_port}/"
            f"{self.query_range_uri}?query=sum({self.prometheus_collection}"
            f"{{{formated_labels}}})&start={self.live_data_start}&end={end}&"
            f"step={self.interval}"
        )
        return url

    def get_history(self, cache_file: str) -> Dict:
        self._validate_filename(cache_file)

        path = f"{self.cache_base_directory}/{cache_file}"

        with open(path, "r") as f:
            return json.load(f)

    def _adapt_format(self, item: List) -> List:
        """Javascript expects timestamps to be in milliseconds
        and counter values as floats

        Args
            item: List of 2 elements, timestamp and counter

        Return:
            Normalized tuple (timestamp in js expected time, counter as float)

        """
        timestamp = int(item[0])
        counter_value = item[1]
        return [timestamp * 1000, float(counter_value)]

    def _get_timestamp_history(self, object: str,) -> List:
        """Return the live values of an object"""
        result = []

        now = int(time.time())

        url = self._compute_url(object=object, end=now,)
        response = requests.get(url)
        if response.ok:
            data = response.json()
            # data answer format:
            # {"status":"success","data":{"result":[{"values":[[1544586427,"5375557897"]...  # noqa
            # Prometheus-provided data has to be adapted to js expectations
            result = [
                self._adapt_format(i) for i in data["data"]["result"][0]["values"]
            ]
        return result

    def refresh_history(
        self, cache_file: str, objects: List[str], static_file: Optional[str] = None,
    ):
        self._validate_filename(cache_file)

        if static_file is not None:
            static_data = self.get_history(static_file)
        else:
            static_data = {}

        # for live content, we retrieve existing data and merges with the new one
        live_data = {}
        for object in objects:
            prometheus_data = self._get_timestamp_history(object=object)
            live_data[object] = static_data.get(object, []) + prometheus_data

        target_file = f"{self.cache_base_directory}/{cache_file}"
        tmp_file = f"{target_file}.tmp"
        with open(tmp_file, "w") as f:
            f.write(json.dumps(live_data))

        os.rename(tmp_file, target_file)
