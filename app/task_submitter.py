import os
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
from .util.log_memory_and_disk_usage import log_memory_and_disk_usage

runtime_env = {"pip": ["requests", "nltk==3.8.1"]}
ray.init(runtime_env=runtime_env)

def wait_for_nodes(required_node_count:int, check_interval=1, timeout=300):
    import time

    start_time = time.time()
    current_node_count = 0

    while True:
        nodes = [node for node in ray.nodes() if node["Alive"] and node["Resources"].get("worker", 0) >=1]
        if len(nodes) >= required_node_count:
            return nodes[:required_node_count]

        if timeout is not None and time.time() - start_time > timeout:
            raise TimeoutError(
                f"Timeout while waiting for {required_node_count} nodes."
            )
        if len(nodes) != current_node_count:
            current_node_count = len(nodes)
            logging.info(
                f"Waiting for {required_node_count} nodes. Currently available: {len(nodes)}"
            )
        time.sleep(check_interval)

class TaskSubmitter:
    def __init__(self, enable_console_logging, tasks: Generator[Task, None, None], task_count: int):
        self.enable_console_logging = enable_console_logging
        self.tasks = tasks
        self.task_count = task_count
        self.nodes = wait_for_nodes(3)  # Ensure at least 3 worker nodes

    def submit_and_process_tasks(self):
        futures = []
        for task in self.tasks:
            futures.append(execute_remote_word_search.options(resources={"worker": 1}).remote(
                task.path_records,
                task.path_prefix,
                self.enable_console_logging,
            ))

        logging.debug(f"---------Number of futures: {len(futures)}")
        
        completed_futures, remaining_futures = [], futures
        searchResults_compressed = []
        
        while remaining_futures:
            done_futures, remaining_futures = ray.wait(remaining_futures, timeout=300)
            for future in done_futures:
                try:
                    result = ray.get(future)
                    searchResults_compressed.append(result)
                except Exception as e:
                    logging.error(f"Task failed with error: {str(e)}")
            
            completed_futures.extend(done_futures)
            logging.debug(f"Completed: {len(completed_futures)}, Remaining: {len(remaining_futures)}")

            if not done_futures:
                logging.warning("No tasks completed in this iteration. Possible stall detected.")

        # log_memory_and_disk_usage()

        # Decompress and deserialize searchResults
        searchResults = [
            json.loads(bz2.decompress(result)) for result in searchResults_compressed
        ]

        # Aggregate node distribution
        node_distribution = {}
        for result in searchResults:
            node_id = result['details']['node_id']
            node_distribution[node_id] = node_distribution.get(node_id, 0) + 1

        for node_id, count in node_distribution.items():
            logging.info(f"Node {node_id} processed {count} tasks")

        return searchResults