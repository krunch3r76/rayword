import ray
import logging
import os
import datetime

from .resourcemonitor import ResourceMonitor
from ..log_memory_and_disk_usage import log_memory_and_disk_usage

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

    time_start = datetime.datetime.now()
    if enable_logging:
        logging.basicConfig(
            level=logging.DEBUG,
            format="---  %(level) -- %(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        )
    if enable_logging:
        logging.debug("\033[1mLOGGING ENABLED ON WORKER {os.getpid()}\033[0m")
    else:
        logging.debug(f"\033[1;33mLOGGING NOT ENABLED ON WORKER {os.getpid()}\033[0m")
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
    # log_memory_and_disk_usage()
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

    time_end = datetime.datetime.now()
    time_delta = time_end - time_start
    resource_monitor.stop()

    logging.debug(
        f"FINISHED WORK SUBMITTING RESULTS TO HEAD NODE, time for work to complete: {str(time_delta)}"
    )
    logging.debug(
        f"""MIN/MAX MEMORY USAGE: {resource_monitor.min_memory_usage / (1024 * 1024)} MB / {resource_monitor.max_memory_usage / (1024 * 1024)} MB"""
    )
    logging.debug(
        f"""MIN/MAX DISK USAGE (/root): {resource_monitor.min_disk_usage / (1024 * 1024)} MB / {resource_monitor.max_disk_usage / (1024 * 1024)} MB"""
    )
    return word_search_results.to_compressed_json()

    # return perform_word_search(words_table, paths_table, path_prefix)
