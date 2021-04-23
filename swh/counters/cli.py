# Copyright (C) 2021  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click

from swh.core.cli import CONTEXT_SETTINGS
from swh.core.cli import swh as swh_cli_group
from swh.counters.kafka_client import KeyOrientedJournalClient


@swh_cli_group.group(name="counters", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--config-file",
    "-C",
    default=None,
    type=click.Path(exists=True, dir_okay=False,),
    help="Configuration file.",
)
@click.pass_context
def counters_cli_group(ctx, config_file):
    """Software Heritage Counters tools."""
    from swh.core import config

    ctx.ensure_object(dict)
    conf = config.read(config_file)
    ctx.obj["config"] = conf


@counters_cli_group.command("journal-client")
@click.option(
    "--stop-after-objects",
    "-m",
    default=None,
    type=int,
    help="Maximum number of objects to replay. Default is to run forever.",
)
@click.option(
    "--object-type",
    "-o",
    multiple=True,
    help="Default list of object types to subscribe to",
)
@click.option(
    "--prefix", "-p", help="Topic prefix to use (e.g swh.journal.objects)",
)
@click.pass_context
def journal_client(ctx, stop_after_objects, object_type, prefix):
    """Listens for new messages from the SWH Journal, and count them
    """
    import functools

    from . import get_counters
    from .journal_client import process_journal_messages

    config = ctx.obj["config"]
    journal_cfg = config["journal"]

    journal_cfg["object_types"] = object_type or journal_cfg.get("object_types", [])
    journal_cfg["prefix"] = prefix or journal_cfg.get("prefix")
    journal_cfg["stop_after_objects"] = stop_after_objects or journal_cfg.get(
        "stop_after_objects"
    )

    if len(journal_cfg["object_types"]) == 0:
        raise ValueError("'object_types' must be specified by cli or configuration")

    if journal_cfg["prefix"] is None:
        raise ValueError("'prefix' must be specified by cli or configuration")

    counters = get_counters(**config["counters"])

    client = KeyOrientedJournalClient(**journal_cfg)

    worker_fn = functools.partial(process_journal_messages, counters=counters)

    nb_messages = 0
    try:
        nb_messages = client.process(worker_fn)
        print("Processed %d messages." % nb_messages)
    except KeyboardInterrupt:
        ctx.exit(0)
    else:
        print("Done.")
    finally:
        client.close()
