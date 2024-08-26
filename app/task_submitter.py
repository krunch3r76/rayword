# app/task_submitter.py
import os

os.environ["RAY_DEDUP_LOGS"] = "0"
import ray
import datetime
import logging
import bz2
import json
from typing import List, Dict, Tuple, Generator
from ray.util.placement_group import (
    placement_group,
    placement_group_table,
    remove_placement_group,
)
from app.task_generator import Task
from app.worker.execute_remote_word_search import execute_remote_word_search
from .log_memory_and_disk_usage import log_memory_and_disk_usage

# from app.worker.wordsearch import WordSearcher

runtime_env = {"pip": ["requests", "nltk==3.8.1"]}
ray.init(runtime_env=runtime_env)


def wait_for_nodes(required_node_count, check_interval=5, timeout=300):
    """
    Waits for the required number of distinct nodes to become available in the Ray cluster.

    Args:
        required_node_count (int): The number of distinct nodes required.
        check_interval (int): Time in seconds between checks for available nodes.
        timeout (int): Maximum time in seconds to wait for the nodes.

    Returns:
        List of node information dictionaries.

    Raises:
        TimeoutError: If the required number of nodes is not available within the timeout.
    """
    import time

    start_time = time.time()

    while True:
        nodes = [node for node in ray.nodes() if node["Alive"]]
        if len(nodes) >= required_node_count:
            return nodes[:required_node_count]

        if timeout is not None and time.time() - start_time > timeout:
            raise TimeoutError(
                f"Timeout while waiting for {required_node_count} nodes."
            )

        logging.info(
            f"Waiting for {required_node_count} nodes. Currently available: {len(nodes)}"
        )
        time.sleep(check_interval)


class TaskSubmitter:
    """
    Manages the submission and processing of tasks for searching words in paths.

    Utilizes Ray to distribute and execute tasks across a cluster, and aggregates results.
    """

    def __init__(self, enable_console_logging=None):
        logging.debug(f"enable_console_logging = {enable_console_logging}")
        if enable_console_logging is None:
            self.enable_console_logging = True if "KRUNCHDEBUG" in os.environ else False
        else:
            self.enable_console_logging = enable_console_logging

    def submit_and_process_tasks(
        self, tasks: Generator[Task, None, None], task_count: int
    ) -> Tuple[List[dict], List[Tuple[int, int]], Dict[str, List[int]]]:
        """
        Submits a list of tasks to the Ray cluster and processes the results.

        Args:
            tasks (Generator[Task, None, None]): Generator of Task objects to be processed.
            task_count (int): The total number of tasks to be processed.

        Returns:
            Tuple[List[dict], List[Tuple[int, int]], Dict[str, List[int]]]: Aggregated word indices,
            search histories, and a summary containing IDs of paths that could not be reached.
        """
        # Get the list of all available nodes
        time_start = datetime.datetime.now()
        nodes = wait_for_nodes(task_count, timeout=None)
        duration_waiting_for_nodes = datetime.datetime.now() - time_start

        # Submit tasks with explicit node assignment
        futures = []
        for i, task in enumerate(tasks):
            node = nodes[i % len(nodes)]
            future = execute_remote_word_search.options(
                scheduling_strategy=ray.util.scheduling_strategies.NodeAffinitySchedulingStrategy(
                    node_id=node["NodeID"], soft=False
                )
            ).remote(
                task.path_records,
                task.path_prefix,
                self.enable_console_logging,
            )
            futures.append(future)

        logging.debug(f"Number of futures: {len(futures)}")
        searchResults_compressed = ray.get(futures)
        log_memory_and_disk_usage()

        # Decompress and deserialize searchResults
        searchResults = [
            json.loads(bz2.decompress(result)) for result in searchResults_compressed
        ]

        return searchResults

    def _submit_and_process_tasks(
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
                task.path_records,
                task.path_prefix,
                self.enable_console_logging,
            )
            for task in tasks
        ]

        logging.debug(f"Number of futures: {len(futures)}")
        searchResults_compressed = ray.get(futures)
        log_memory_and_disk_usage()
        # Decompress and deserialize searchResults
        searchResults = [
            json.loads(bz2.decompress(result)) for result in searchResults_compressed
        ]

        return searchResults
