#!/usr/bin/env python3
# main/prepare_unsearched_paths_json.py
# connect to main db and write json file with paths for head node to task with indexing
from pathlib import Path
import json
import logging
import sys
import os
import argparse
import re

PATH_TO_PROJECT_ROOTDIR = Path(__file__).parent.parent
sys.path.insert(0, str(PATH_TO_PROJECT_ROOTDIR))

from model.maindbmodel import MainModel

PATH_TO_HEAD_INPUT_DIR = Path("./app/input").absolute()


def prepare_unsearched_paths_json(max_paths, path_to_db, path_to_targets_db):
    # instantiate model
    mainModel = MainModel(main_db_path=path_to_db, paths_db_path=path_to_targets_db)
    # get unsearched
    unsearched_path_records_as_dict = mainModel.get_unsearched_path_records(
        max_paths=max_paths, to_json=False
    )
    # write to file
    with open(
        PATH_TO_HEAD_INPUT_DIR / "path_records_unsearched.json", "w", encoding="utf-8"
    ) as file:
        json.dump(unsearched_path_records_as_dict, file, ensure_ascii=False)

    return mainModel.get_total_texts_and_unsearched_counts()


def get_max_workers_from_config(yaml_config_path):
    """parse the yaml config file for the maximum number of workers"""
    max_workers_pattern = re.compile(r"max_workers:\s*(\d+)")

    with open(yaml_config_path, "r") as file:
        for line in file:
            match = max_workers_pattern.search(line)
            if match:
                return int(match.group(1))
    return None


if __name__ == "__main__":
    # Setup logging
    log_level = "DEBUG" if "KRUNCHDEBUG" in os.environ else "WARNING"
    logging.basicConfig(
        level=log_level,
        format="%(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s",
    )

    # Setup argparse
    parser = argparse.ArgumentParser(description="Process unsearched paths.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for processing unsearched paths",
    )
    parser.add_argument(
        "yaml_config_path", type=str, help="Path to the YAML configuration file"
    )
    args = parser.parse_args()

    # Use the arguments
    batch_size = args.batch_size
    yaml_config_path = Path(args.yaml_config_path).absolute()

    # Export batch_size as JSON
    args_dict = {"batch_size": batch_size}
    output_dir = Path("./app/input")
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "batch_size_config.json", "w") as f:
        json.dump(args_dict, f, indent=4)

    PATH_TO_MAIN_DB = Path("./data/main.db").absolute()
    PATH_TO_TARGETS_DB = Path("./data/paths.db").absolute()

    max_workers = get_max_workers_from_config(yaml_config_path)
    path_limit = batch_size * max_workers
    total_texts, unsearched_count = prepare_unsearched_paths_json(
        path_limit, path_to_db=PATH_TO_MAIN_DB, path_to_targets_db=PATH_TO_TARGETS_DB
    )

    print(f"{unsearched_count} texts out of {total_texts} have not been indexed")
    number_of_texts_to_search_on_this_run = (
        path_limit if path_limit >= unsearched_count else unsearched_count
    )
    print(f"attempting to index {path_limit} texts on ray")
    logging.debug(
        f"selecting at most a total of {path_limit} paths to search"
        + f" based on max workers of {max_workers} and batch size of {batch_size}"
    )
