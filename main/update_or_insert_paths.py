#!/usr/bin/env python3
# main/update_or_insert_paths.py
from pathlib import Path
import sys
import logging

PATH_TO_PROJECT_ROOTDIR = Path(__file__).parent.parent
sys.path.insert(0, str(PATH_TO_PROJECT_ROOTDIR))

from app.util.resource import parse_resources_file
from model.maindbmodel import MainModel


PATH_TO_MAIN_DB = Path("./data/main.db").absolute()
PATH_TO_TARGETS_DB = Path("./data/paths.db").absolute()
PATH_TO_TARGETS = Path("./data/targets.txt").absolute()


def update_or_insert_paths():
    mainModel = MainModel(PATH_TO_MAIN_DB, PATH_TO_TARGETS_DB)
    with open(PATH_TO_TARGETS) as f:
        resources = parse_resources_file(f)
        paths_and_text_numbers = [
            (resource.get_path(), Path(resource.get_path()).parent.name)
            for resource in resources
        ]
    mainModel.update_or_insert_paths(paths_and_text_numbers)


if __name__ == "__main__":
    import os

    log_level = "DEBUG" if "KRUNCHDEBUG" in os.environ else "WARNING"
    logging.basicConfig(
        level=log_level,
        format="%(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s",
    )
    update_or_insert_paths()
