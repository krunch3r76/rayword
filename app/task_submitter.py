# app/task_submitter.py
import ray
import logging
import os
from typing import List, Dict, Tuple

from app.task_generator import Task
from app.worker.execute_remote_word_search import execute_remote_word_search

# from app.worker.wordsearch import WordSearcher

runtime_env = {"pip": ["nltk==3.8.1", "requests"]}
ray.init(runtime_env=runtime_env)


class TaskSubmitter:
    """
    Manages the submission and processing of tasks for searching words in paths.

    Utilizes Ray to distribute and execute tasks across a cluster, and aggregates results.
    """

    def __init__(self, enable_console_logging=None):
        if enable_console_logging is None:
            self.enable_logging = True if "KRUNCHDEBUG" in os.environ else False
        else:
            self.enable_console_logging = enable_console_logging

    def submit_and_process_tasks(
        self, tasks: List[Task]
    ) -> Tuple[List[dict], List[Tuple[int, int]], Dict[str, List[int]]]:
        """
        Submits a list of tasks to the Ray cluster and processes the results.

        Args:
            tasks (List[Task]): List of Task objects to be processed.

        Returns:
            Tuple[List[dict], List[Tuple[int, int]], Dict[str, List[int]]]: Aggregated word indices,
            search histories, and a summary containing IDs of paths that could not be reached.
        """
        futures = [
            execute_remote_word_search.remote(
                task.word_records,
                task.path_records,
                task.path_prefix,
                self.enable_console_logging,
            )
            for task in tasks
        ]

        logging.debug(f"Number of futures: {len(futures)}")
        searchResults = ray.get(futures)

        word_indices_aggregated, search_histories, bad_path_ids = [], [], set()
        for searchResult in searchResults:
            word_indices_aggregated.extend(searchResult["word_indices"])
            search_histories.extend(searchResult["search_histories"])
            bad_path_ids.update(searchResult["unreachable_path_ids"])

        summary = {"bad_path_ids": list(bad_path_ids)}
        return word_indices_aggregated, search_histories, summary
