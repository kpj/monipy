"""
Interfacing with various database formats (e.g. RRD).
"""

import os
import datetime
import tempfile
import itertools
import collections
from pathlib import Path
from base64 import b64encode

import rrdtool
import pandas as pd

import palettable
from loguru import logger
from natsort import natsorted

from .__version__ import __version__


def get_ds_names(fname):
    # TODO: there must be a better way!?
    ds_list = list(
        set(
            k.split(".")[0]
            for k in rrdtool.info(str(fname)).keys()
            if k.startswith("ds")
        )
    )

    # if len(ds_list) != 1:
    #     logger.warning(
    #         f"Found more than one data source ({ds_list})]"
    #     )

    return natsorted([ds[3:-1] for ds in ds_list])


def generate_legend_names(fname_list):
    # assmble name for each data line
    name_dict = collections.defaultdict(list)
    for fname in fname_list:
        for ds in get_ds_names(fname):
            name = (
                "-".join(fname.stem.split("-")[1:]) if "-" in fname.stem else fname.stem
            )
            if ds != "value":
                name += f"_{ds}"

            name_dict[fname].append(name)

    # remove common prefixes
    prefix = os.path.commonprefix([v for vals in name_dict.values() for v in vals])
    if prefix:
        for fname in fname_list:
            name_dict[fname] = [n[len(prefix) :] for n in name_dict[fname]]

    # align based on lengths
    max_len = max([len(v) for vals in name_dict.values() for v in vals])
    for fname in fname_list:
        name_dict[fname] = [
            n if len(n) == max_len else n + " " * (max_len - len(n))
            for n in name_dict[fname]
        ]

    # finalize
    return dict(name_dict)


def assemble_definitions(fname, color_list, name_list):
    res = []

    for ds, name, color in zip(get_ds_names(fname), name_list, color_list):
        id_ = f"{fname.stem}__{ds}"

        res.extend(
            (
                f"DEF:{id_}={fname}:{ds}:AVERAGE",
                f"LINE1:{id_}{color}:{name}",
                f"GPRINT:{id_}:LAST:%8.2lf %s",
                f"GPRINT:{id_}:MIN:%8.2lf %s",
                f"GPRINT:{id_}:AVERAGE:%8.2lf %s",
                f"GPRINT:{id_}:MAX:%8.2lf %s\\n",
            )
        )

    return res


def rrd2svg(fname_list, title, start_time=None, end_time=None):
    all_colors = palettable.tableau.Tableau_10.hex_colors
    # if len(fname_list) > len(color_list):
    #     logger.warning(f"Skipping {title}, too many files ({fname_list})")
    #     return ""
    # assert len(fname_list) <= len(color_list), fname_list

    with tempfile.NamedTemporaryFile() as fd:
        # pre-assemble names to adjust their lengths
        name_dict = generate_legend_names(fname_list)

        # assemble color list
        color_dict = {}
        for key, list_ in name_dict.items():
            if len(all_colors[: len(list_)]) != len(list_):
                logger.error(f"Exhausted color list with {title}")

            color_dict[key] = all_colors[: len(list_)]
            del all_colors[: len(list_)]

        # parse input files
        def_list = itertools.chain.from_iterable(
            [
                assemble_definitions(fname, color_dict[fname], name_dict[fname])
                for fname in fname_list
            ]
        )

        # determine timeframe
        time_spec = []
        if start_time is not None:
            time_spec.extend(["--start", str(int(start_time.timestamp()))])
        if end_time is not None:
            time_spec.extend(["--end", str(int(end_time.timestamp()))])

        # get timestamp of latest data point
        timestamp_list = [
            rrdtool.lastupdate(str(fname))["date"] for fname in fname_list
        ]
        if len(set(timestamp_list)) > 1:
            logger.warning(
                f"Single plot has multiple last timepoints: {timestamp_list}"
            )

        last_update_ts = max(timestamp_list).strftime(r"%Y-%m-%d %H\:%M\:%S")

        # generate graph
        width, height, _ = rrdtool.graph(
            fd.name,
            "--imgformat",
            "PNG",  # "SVG",
            "--title",
            title,
            "--width",
            "400",
            "--height",
            "100",
            "--watermark",
            f"monipy {__version__}",
            "--alt-autoscale",
            "--slope-mode",
            *time_spec,
            *def_list,
            "TEXTALIGN:right",
            rf"COMMENT:Last update\: {last_update_ts}",
        )

        return b64encode(fd.read()).decode()


if __name__ == "__main__":
    with open("foo.svg", "w") as fd:
        fd.write(
            rrd2svg(
                [
                    Path("collectd/rpi4/memory/memory-free.rrd"),
                    Path("collectd/rpi4/memory/memory-used.rrd"),
                ],
                "Wow",
            )
        )
