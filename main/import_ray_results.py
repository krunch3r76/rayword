#!/usr/bin/env python3
# /main/import_ray_results.py
import json
import bz2
from pathlib import Path
import logging
import time

from model.maindbmodel import MainModel

PATH_TO_MAIN_DB = Path("./data/main.db").absolute()
PATH_TO_PATHS_DB = Path("./data/paths.db").absolute()


def insert_word_indices(mainModel, word_indices_records):
    word_id_cache = {}  # Cache for word_id lookups
    word_indices_to_insert = []  # Collect word indices for batch insertion

    for record in word_indices_records:
        word = record["word"]
        word_index = record["word_index"]
        text_number = record["text_number"]

        # Use cache if available; otherwise, look up or insert the word to get word_id
        if word not in word_id_cache:
            word_id = mainModel.get_word_id(word)
            if word_id is None:
                word_id = mainModel.insert_word(word)
            word_id_cache[word] = word_id
        else:
            word_id = word_id_cache[word]

        # Add to the batch insertion list
        word_indices_to_insert.append((word_id, word_index, text_number))

    # Batch insert word indices
    if word_indices_to_insert:
        mainModel.insert_into_word_indices(word_indices_to_insert)


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


def import_ray_results(
    text_numbers_searched_list_path, bad_paths_list_path, word_indices_compressed_path
):
    mainModel = MainModel(PATH_TO_MAIN_DB, PATH_TO_PATHS_DB)

    text_numbers_searched_list = read_json_from_file(text_numbers_searched_list_path)
    bad_path_list = read_json_from_file(bad_paths_list_path)

    start_time = time.time()
    with bz2.open(word_indices_compressed_path, "rb") as f:
        decompressed_data = f.read()
    logging.debug(f"decompression took {time.time() - start_time} seconds")
    start_time = time.time()
    word_indices_records = json.loads(decompressed_data)
    logging.debug(
        f"loading records into memory took {time.time() - start_time} seconds"
    )

    try:
        # Start a transaction
        mainModel.db_connection.execute("BEGIN")

        # Perform updates
        start_time = time.time()
        mainModel.insert_search_histories(text_numbers_searched_list)
        logging.debug(
            f"insert_search_histories took {time.time() - start_time} seconds"
        )

        start_time = time.time()
        mainModel.mark_texts_unreachable(bad_path_list)
        logging.debug(f"mark_texts_unreachable took {time.time() - start_time} seconds")

        start_time = time.time()
        insert_word_indices(mainModel, word_indices_records)
        logging.debug(f"insert_word_indices took {time.time() - start_time} seconds")

        # Commit the transaction
        mainModel.db_connection.commit()
    except Exception as e:
        # Rollback in case of an error
        mainModel.db_connection.rollback()
        logging.error(f"Error during import_ray_results: {e}")
        raise


if __name__ == "__main__":
    import os

    log_level = "DEBUG" if "KRUNCHDEBUG" in os.environ else "WARNING"
    logging.basicConfig(
        level=log_level,
        format="%(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s",
    )
    PATH_TO_RAY_OUTPUT_DIR = Path("./app/output")
    PATH_TO_TEXTS_SEARCHED_JSON = PATH_TO_RAY_OUTPUT_DIR / "text_numbers_searched.json"
    PATH_TO_UNREACHABLE_PATHS_JSON = PATH_TO_RAY_OUTPUT_DIR / "unreachable_paths.json"
    PATH_TO_WORDINDICES_COMPRESSED = PATH_TO_RAY_OUTPUT_DIR / "WordIndices.json.bz2"
    import_ray_results(
        PATH_TO_TEXTS_SEARCHED_JSON,
        PATH_TO_UNREACHABLE_PATHS_JSON,
        PATH_TO_WORDINDICES_COMPRESSED,
    )
