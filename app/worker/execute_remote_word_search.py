import ray
import logging
import psutil
import threading
import time
import os

from .resourcemonitor import ResourceMonitor

# runtime_env = {"pip": ["requests", "nltk"]}
# ray.init(runtime_env=runtime_env)


@ray.remote
def execute_remote_word_search(paths_table, path_prefix=None, enable_logging=False):
    """
    Executes a search for words in the given paths, run as a Ray remote function.

    Args:
        words_table (list): List of dictionaries representing word records.
        paths_table (list): List of dictionaries representing path records.
        path_prefix (str, optional): Optional prefix for paths.

    Returns:
        Tuple[List[dict], Dict]: Tuple containing the search results and history information.
    """
    # logging.getLogger().setLevel(logging.WARNING)
    from .wordsearch import WordSearcher

    if enable_logging:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        )

    resource_monitor = ResourceMonitor()

    EXCLUSIONS_FILE = "/root/app/worker/exclusions.txt"
    current_directory = os.getcwd()
    try:
        with open(EXCLUSIONS_FILE, "r") as file:
            exclusions = {line.strip() for line in file}
        logging.debug(
            f"Loaded exclusions file '{EXCLUSIONS_FILE}' from directory '{current_directory}'"
        )
    except FileNotFoundError:
        logging.error(
            f"Exclusions file '{EXCLUSIONS_FILE}' not found in directory '{current_directory}'."
        )
        exclusions = set()

    word_searcher = WordSearcher(
        paths_table, path_prefix=path_prefix, exclude_words=exclusions
    )

    word_search_results = word_searcher.perform_search()

    resource_monitor.stop()

    logging.debug(
        f"MAX MEMORY USAGE: {resource_monitor.max_memory_usage / (1024 * 1024)} MB"
    )
    logging.debug(
        f"MAX DISK USAGE: {resource_monitor.max_disk_usage / (1024 * 1024)} MB"
    )
    return word_search_results.to_compressed_json()

    # return perform_word_search(words_table, paths_table, path_prefix)
