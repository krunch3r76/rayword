#!/usr/bin/env python3
# rayword.py
# setup and run

import logging
from pathlib import Path
import os
import re
import subprocess

from app.controller import Controller
from app.model import WordIndexerModel
from constants import TARGETS_FILE
from app.util.resource import parse_resources_file


def get_max_workers_from_config(yaml_config_path):
    """parse the yaml config file for the maximum number of workers"""
    max_workers_pattern = re.compile(r"max_workers:\s*(\d+)")

    with open(yaml_config_path, "r") as file:
        for line in file:
            match = max_workers_pattern.search(line)
            if match:
                return int(match.group(1))
    return None


def find_word_forms(word):
    """leverage nltk (if available) to find all the forms of the word being searched

    Args:
        word: the word searched for

    Returns:
        list (str): the word searched for and other forms (if any) found
    """
    try:
        import nltk

        nltk_data_dir = Path(__file__) / "nltk_data"
        nltk.data.path.append(str(nltk_data_dir))
        from word_forms.word_forms import get_word_forms
    except (NameError, ModuleNotFoundError):
        return [word]
    else:
        word_forms_data = get_word_forms(word)
        combined_set = set()
        for forms in word_forms_data.values():
            combined_set.update(forms)
        return list(combined_set)


def main(args):
    # formatter = logging.Formatter(">>>%(filename)s:%(lineno)d - %(message)s")
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Set the lowest log level you need globally

    # Create a file handler for DEBUG and above
    file_handler = logging.FileHandler("debug.log", mode="w")
    file_handler.setLevel(logging.DEBUG)  # Set the log level for this handler
    file_formatter = logging.Formatter(
        "%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Create a console handler for INFO and above
    console_handler = logging.StreamHandler()
    if "KRUNCHDEBUG" in os.environ or args.enable_console_logging:
        console_handler.setLevel(logging.DEBUG)
        # ANSI escape codes
        ESC_START = "\033["
        ESC_END = "\033[0m"
        BLINK = "5m"
        RED = "31m"  # Example color - red

        debug_console_formatter = logging.Formatter(
            f"{ESC_START}{RED}{ESC_START}{BLINK}%(levelname)s{ESC_END} - %(asctime)s - %(filename)s:%(lineno)d - %(message)s"
        )
        console_formatter = debug_console_formatter
    else:
        console_handler.setLevel(logging.INFO)  # Set the log level for this handler
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    primary_word = args.word
    words = [primary_word]
    word_forms = find_word_forms(primary_word)
    if len(word_forms) == 0:
        raise Exception(
            "Uh oh, it seems the word you are searching for is not a known English word! Aborting!"
        )

    max_workers = get_max_workers_from_config("golem-cluster.yaml")
    # instantiate model
    managerModel = WordIndexerModel(path_limit=max_workers * args.batch_size)

    # update model with any new urls
    resources = None
    with open(TARGETS_FILE) as f:
        resources = parse_resources_file(f)
    paths_and_text_numbers = [
        (resource.get_path(), Path(resource.get_path()).parent.name)
        for resource in resources
    ]
    managerModel.update_or_insert_paths(paths_and_text_numbers)

    # update model with an new words
    print(f"updating model with {word_forms}")
    managerModel.update_or_insert_word_groups(words)

    # check model for highest indexed WordIndices
    last_word_index_row_id = managerModel.get_max_word_indices_id()

    ############################ START CONTROLLER ###############################
    controller = Controller(managerModel, args.batch_size)
    controller(primary_word, enable_console_logging=args.enable_console_logging)
    #############################################################################

    count_inserted = managerModel.update_insertion_history()

    # count_inserted = managerModel.get_count_records_last_added()
    if count_inserted >= -1:
        if count_inserted >= 1:
            print(f"A total of {count_inserted} instances of the word(s) were inserted")
        # logging.debug(f"last_word_index_row_id: {last_word_index_row_id}")
        random_index = managerModel.get_random_word_index_above_id(
            last_word_index_row_id, primary_word
        )
        if random_index is None:
            random_index = managerModel.get_random_word_index_above_id(words)

        random_context_sentence = random_index["context_sentence"]
        print()
        print(random_context_sentence, flush=True)
        print()
        random_context_sentence_stripped = random_context_sentence.replace("\r\n", " ")
        env = os.environ.copy()
        env["PATH"] = "/espeak/bin:" + env["PATH"]
        subprocess.run(
            [
                "espeak",
                "-v",
                "en-us",
                "-p",
                "45",
                "-s",
                "120",
                "-a",
                "110",
                "-g",
                "10",
                "-k",
                "5",
                f"{random_context_sentence_stripped}",
                "-w",
                "./app/output/sample.wav",
            ],
            env=env,
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Rayword application.")
    parser.add_argument("word", help="The primary word to process")
    parser.add_argument(
        "--enable-console-logging",
        action="store_true",
        help="print debug log messages",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=150,
        help="Maximum number of paths a worker will be assigned at most",
    )

    args = parser.parse_args()

    main(args)
