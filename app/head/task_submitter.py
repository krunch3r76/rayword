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
from app.head.task_generator import Task
from app.worker.execute_remote_word_search import execute_remote_word_search
from app.utils.monitoring.resource_monitor import log_memory_and_disk_usage

runtime_env = {"pip": ["requests", "nltk==3.8.1"]}
ray.init(runtime_env=runtime_env)

def wait_for_nodes(required_node_count:int, check_interval=1, timeout=6000):
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
        required_nodes = min(10, task_count)  # Adjust the number of required nodes based on task count
        self.nodes = wait_for_nodes(required_nodes)

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
        max_retries = 3
        future_retries = {future: 0 for future in futures}
        max_stall_iterations = 5
        stall_iterations = 0
        
        while remaining_futures:
            logging.debug(f"Waiting for futures. Remaining: {len(remaining_futures)}")
            done_futures, remaining_futures = ray.wait(remaining_futures, num_returns=len(remaining_futures), timeout=6000)
            if not done_futures:
                stall_iterations += 1
                logging.warning("No tasks completed in this iteration. Possible stall detected.")
                if stall_iterations >= max_stall_iterations:
                    logging.critical("Stall detected: No tasks completed for multiple iterations. Exiting.")
                    break
            else:
                stall_iterations = 0  # Reset stall counter if tasks complete

            for future in done_futures:
                try:
                    result = ray.get(future)  # Attempt to get the result of the future
                    searchResults_compressed.append(result)
                    future_retries.pop(future, None)  # Remove from retries tracking
                except Exception as e:
                    logging.error(f"Task failed with error: {str(e)}")  # Log the error
                    if future_retries[future] < max_retries:
                        future_retries[future] += 1
                        remaining_futures.append(future)  # Retry the future
                    else:
                        logging.error(f"Task failed after {max_retries} retries: {str(e)}")
                        future_retries.pop(future, None)  # Remove from retries tracking
            
            completed_futures.extend(done_futures)
            logging.debug(f"Completed: {len(completed_futures)}, Remaining: {len(remaining_futures)}")

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