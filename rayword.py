#!/usr/bin/env python3

import logging
import traceback

logging.basicConfig(
    filename="wtf.log",
    filemode="w",
    level=logging.DEBUG,
    format="%(filename)s %(lineno)s %(msg)s",
)
from start_indexing.controller import Controller

cmds = [
    ["echo", "'Hello, worlds!'"],
    ["rm", "-f", "app/output/*"],
    ["python3", "main/update_or_insert_paths.py"],
    [
        "python3",
        "main/prepare_unsearched_paths_json.py",
        "golem-cluster.yaml",
        "--batch-size",
        "50",
    ],
    ["ray", "up", "golem-cluster.yaml", "--yes", "--no-config-cache"],
    [
        "ray",
        "rsync-up",
        "golem-cluster.yaml",
        "./app/input/",
        "/root/app/input/",
    ],
    [
        "ray",
        "submit",
        "golem-cluster.yaml",
        "./rayword_executor.py",
        "--enable-console-logging",
    ],
    [
        "ray",
        "rsync-down",
        "golem-cluster.yaml",
        "/root/app/output/",
        "./app/output",
    ],
    ["python3", "main/import_ray_results.py"],
    ["ray", "down", "golem-cluster.yaml", "--yes"],
]
controller = Controller(cmds)
try:
    controller()
except Exception as e:
    logging.debug(f"an exception {e} of type {type(e)} occurred")
    logging.debug(traceback.format_exc())
    del controller
