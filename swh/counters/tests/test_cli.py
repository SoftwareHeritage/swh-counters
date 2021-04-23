# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import copy
import tempfile

from click.testing import CliRunner
from confluent_kafka import Producer
import pytest
import yaml

from swh.counters.cli import counters_cli_group
from swh.journal.serializers import value_to_kafka

CLI_CONFIG = """
counters:
    cls: redis
    host: %(redis_host)s
"""

JOURNAL_OBJECTS_CONFIG_TEMPLATE = """
journal:
    brokers:
        - {broker}
    prefix: {prefix}
    group_id: {group_id}
"""


def invoke(catch_exceptions, args, config="", *, redis_host):
    runner = CliRunner()
    with tempfile.NamedTemporaryFile("a", suffix=".yml") as config_fd:
        config_fd.write((CLI_CONFIG + config) % {"redis_host": redis_host})
        config_fd.seek(0)
        result = runner.invoke(counters_cli_group, ["-C" + config_fd.name] + args)
    if not catch_exceptions and result.exception:
        print(result.output)
        raise result.exception
    return result


def test__journal_client__worker_function_invoked(
    mocker, kafka_server, kafka_prefix, journal_config, local_redis_host
):
    mock = mocker.patch("swh.counters.journal_client.process_journal_messages")

    producer = Producer(
        {
            "bootstrap.servers": kafka_server,
            "client.id": "test-producer",
            "acks": "all",
        }
    )
    topic = f"{kafka_prefix}.content"
    value = value_to_kafka({"key": "value"})
    producer.produce(topic=topic, key=b"message1", value=value)

    invoke(
        False,
        # Missing --object-types (and no config key) will make the cli raise
        ["journal-client", "--stop-after-objects", "1", "--object-type", "content",],
        journal_config,
        redis_host=local_redis_host,
    )

    assert mock.call_count == 1


def test__journal_client__missing_main_journal_config_key(local_redis_host):
    """Missing configuration on journal should raise"""
    with pytest.raises(KeyError, match="journal"):
        invoke(
            catch_exceptions=False,
            args=["journal-client", "--stop-after-objects", "1"],
            config="",  # missing config will make it raise
            redis_host=local_redis_host,
        )


def test__journal_client__missing_journal_config_keys(local_redis_host):
    """Missing configuration on mandatory journal keys should raise"""
    kafka_prefix = "swh.journal.objects"
    journal_objects_config = JOURNAL_OBJECTS_CONFIG_TEMPLATE.format(
        broker="192.0.2.1", prefix=kafka_prefix, group_id="test-consumer"
    )
    journal_config = yaml.safe_load(journal_objects_config)

    for key in journal_config["journal"].keys():
        if key == "prefix":  # optional
            continue
        cfg = copy.deepcopy(journal_config)
        del cfg["journal"][key]  # make config incomplete
        yaml_cfg = yaml.dump(cfg)

        with pytest.raises(TypeError, match=f"{key}"):
            invoke(
                catch_exceptions=False,
                args=[
                    "journal-client",
                    "--stop-after-objects",
                    "1",
                    "--prefix",
                    kafka_prefix,
                    "--object-type",
                    "content",
                ],
                config=yaml_cfg,  # incomplete config will make the cli raise
                redis_host=local_redis_host,
            )


def test__journal_client__missing_prefix_config_key(kafka_server, local_redis_host):
    """Missing configuration on mandatory prefix key should raise"""

    journal_cfg_template = """
journal:
    brokers:
        - {broker}
    group_id: {group_id}
    """

    journal_cfg = journal_cfg_template.format(
        broker=kafka_server, group_id="test-consumer"
    )

    with pytest.raises(ValueError, match="prefix"):
        invoke(
            False,
            # Missing --prefix (and no config key) will make the cli raise
            [
                "journal-client",
                "--stop-after-objects",
                "1",
                "--object-type",
                "content",
            ],
            journal_cfg,
            redis_host=local_redis_host,
        )


def test__journal_client__missing_object_types_config_key(
    kafka_server, local_redis_host
):
    """Missing configuration on mandatory object-types key should raise"""

    journal_cfg = JOURNAL_OBJECTS_CONFIG_TEMPLATE.format(
        broker=kafka_server, prefix="swh.journal.objects", group_id="test-consumer"
    )

    with pytest.raises(ValueError, match="object_types"):
        invoke(
            False,
            # Missing --object-types (and no config key) will make the cli raise
            ["journal-client", "--stop-after-objects", "1"],
            journal_cfg,
            redis_host=local_redis_host,
        )


def test__journal_client__key_received(mocker, kafka_server, local_redis_host):
    mock = mocker.patch("swh.counters.journal_client.process_journal_messages")
    mock.return_value = 1

    prefix = "swh.journal.objects"
    object_type = "content"
    topic = prefix + "." + object_type

    producer = Producer(
        {"bootstrap.servers": kafka_server, "client.id": "testproducer", "acks": "all",}
    )

    value = value_to_kafka({"key": "value"})
    key = b"message key"

    # Ensure empty messages are ignored
    producer.produce(topic=topic, key=b"emptymessage", value=None)
    producer.produce(topic=topic, key=key, value=value)
    producer.flush()

    journal_cfg = JOURNAL_OBJECTS_CONFIG_TEMPLATE.format(
        broker=kafka_server, prefix=prefix, group_id="test-consumer"
    )

    result = invoke(
        False,
        [
            "journal-client",
            "--stop-after-objects",
            "1",
            "--object-type",
            object_type,
            "--prefix",
            prefix,
        ],
        journal_cfg,
        redis_host=local_redis_host,
    )

    # Check the output
    expected_output = "Processed 1 messages.\nDone.\n"
    assert result.exit_code == 0, result.output
    assert result.output == expected_output
    assert mock.called
    assert mock.call_args[0][0]["content"]
    assert len(mock.call_args[0][0]) == 1
    assert object_type in mock.call_args[0][0].keys()
