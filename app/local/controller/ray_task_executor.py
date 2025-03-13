#!/usr/bin/env python3
# rayword.py
# head script
import json
from pathlib import Path
import logging
import argparse
import os

from app.head.model.wordindexermodel import WordIndexerModel
from app.head.controller import Controller

# File path constants
CONFIG_PATH = Path("./app/head/input/batch_size_config.json")
PATH_TO_RECORDS_FILE = Path("./app/head/input/path_records_unsearched.json")
RAY_OUTPUT_DIR = Path("./app/head/output")
UNREACHABLE_PATHS_FILE = RAY_OUTPUT_DIR / "unreachable_paths.json"
TEXT_NUMBERS_SEARCHED_FILE = RAY_OUTPUT_DIR / "text_numbers_searched.json"
WORD_INDICES_FILE = RAY_OUTPUT_DIR / "WordIndices.json.bz2"


def read_json_from_file(file_path):
    """
    Read JSON data from a file and return it as a Python object.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        The Python object decoded from JSON.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except IOError as e:
        print(f"Error reading file: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Rayword application.")
    # parser.add_argument("word", help="The primary word to process")
    parser.add_argument(
        "--enable-console-logging",
        action="store_true",
        default=False,
        help="print debug log messages",
    )

    args = parser.parse_args()
    if args.enable_console_logging:
        os.environ["KRUNCHDEBUG"] = "1"
    
    # Setup logging
    log_level = "DEBUG" if "KRUNCHDEBUG" in os.environ else "INFO"
    log_level = "DEBUG" if args.enable_console_logging else "INFO"
    logging.basicConfig(
        level=log_level,
        format="%(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s",
    )

    # Read batch_size from JSON
    config_data = read_json_from_file(CONFIG_PATH)
    batch_size = config_data.get("batch_size") if config_data else None

    enable_console_logging = args.enable_console_logging

    # instantiate model
    path_records_to_insert = read_json_from_file(PATH_TO_RECORDS_FILE)
    rayword_model = WordIndexerModel(path_records_to_insert)

    #########################################
    # instantiate & call controller         #
    #########################################
    rayword_controller = Controller(rayword_model, batch_size=batch_size)
    summary = rayword_controller(enable_console_logging=enable_console_logging)

    # export results to output after controller finishes
    # # unreachable paths
    unreachable_path_ids = rayword_model.get_unreachable_paths()
    with open(str(UNREACHABLE_PATHS_FILE), "w", encoding="utf-8") as f:
        json.dump(unreachable_path_ids, f, ensure_ascii=False)
    
    # # text numbers searched
    text_numbers_searched = rayword_model.get_text_numbers_searched()
    with open(str(TEXT_NUMBERS_SEARCHED_FILE), "w", encoding="utf-8") as f:
        json.dump(text_numbers_searched, f, ensure_ascii=False)

    # # word indices
    rayword_model.export_table_to_file(
        "WordIndices", str(WORD_INDICES_FILE), compress=True
    )
    # /export results to output
