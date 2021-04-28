"""
Interfacing with various resource collection tools (e.g. collectd).
"""

import datetime
import collections
from pathlib import Path

from natsort import natsorted

from .databases import rrd2svg


def handle_collectd(root_dir):
    """Generate figure for each plugin for each hoster."""
    result = collections.defaultdict(lambda: collections.defaultdict(dict))
    for host in natsorted(root_dir.iterdir()):
        for plugin in natsorted(host.iterdir()):
            stats_list = natsorted(
                [fname for fname in plugin.iterdir() if fname.suffix == ".rrd"]
            )
            title = plugin.name

            result[host.name][plugin.name] = {
                "daily": rrd2svg(
                    stats_list,
                    f"{title} - by day",
                    start_time=datetime.datetime.now() - datetime.timedelta(days=1),
                ),
                "monthly": rrd2svg(
                    stats_list,
                    f"{title} - by month",
                    start_time=datetime.datetime.now() - datetime.timedelta(weeks=4),
                ),
            }

            if len(result[host.name]) > 20:
                break
    return result


if __name__ == "__main__":
    figure_map = handle_collectd(Path("collectd/"))
    print(figure_map)
