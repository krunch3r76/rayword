# app/controller.py
from .task_submitter import TaskSubmitter
from .task_generator import TaskGenerator
import logging
from dataclasses import dataclass
from typing import Optional, List
import os
import psutil
import subprocess
from .log_memory_and_disk_usage import log_memory_and_disk_usage

@dataclass
class SearchSummary:
    all_targets_already_searched: bool
    num_paths_searched: Optional[int] = None
    num_unreachable_paths: Optional[int] = None
    node_distribution: Optional[List[dict]] = None

def get_node_ip():
    import socket

    # Get the non-loopback IP address directly from network interfaces
    ip_address = None
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                ip_address = addr.address
                break
        if ip_address:
            break

    if not ip_address:
        ip_address = "Unknown"

    return ip_address


import logging
import os
from app.task_submitter import TaskSubmitter
from app.task_generator import TaskGenerator
from .log_memory_and_disk_usage import log_memory_and_disk_usage

class Controller:
    def __init__(self, model, batch_size, view=None):
        self.model = model
        self.view = view
        self.enable_console_logging = None
        self.batch_size = batch_size

    def __call__(self, enable_console_logging=False):
        self.enable_console_logging = enable_console_logging
        unsearched_path_records = self.model.get_path_records()

        if len(unsearched_path_records) > 0:
            return self._distribute_word_search_tasks(unsearched_path_records)
        else:
            return SearchSummary(all_targets_already_searched=True)

    def _distribute_word_search_tasks(self, unsearched_paths):
        """
        distributes word search tasks to workers
        returns summary of search results
        """
        logging.debug(
            f"Hello from controller with pid {os.getpid()} at ip address: {get_node_ip()}"
        )
        # log_memory_and_disk_usage()
        task_generator = TaskGenerator(batch_size=self.batch_size)

        path_prefix = os.environ.get("RAYWORD_URL_PREFIX", None)
        task_count = len(unsearched_paths) // self.batch_size
        task_batches = task_generator.generate(unsearched_paths, path_prefix)

        task_submitter = TaskSubmitter(enable_console_logging=self.enable_console_logging, tasks=task_batches, task_count=task_count)
        searchResults = task_submitter.submit_and_process_tasks()

        word_indices_aggregated, search_histories_aggregated, bad_path_ids, details = (
            [],
            [],
            set(),
            []
        )


        for searchResult in searchResults:
            search_histories_aggregated.extend(searchResult["paths_searched"])
            word_positions_by_paths = searchResult["word_positions_by_paths"]
            for path, word_positions in word_positions_by_paths.items():
                # lookup textnumber
                text_number = self.model.lookup_text_number_by_path(path)
                for word, positions in word_positions.items():
                    for position in positions:
                        wordIndex = {
                            "word": word,
                            "word_index": position,
                            "text_number": text_number,
                        }
                        word_indices_aggregated.append(wordIndex)
            bad_path_ids.update(searchResult["bad_paths"])
            details.extend(searchResult["details"])

        self.model.insert_search_histories(search_histories_aggregated)
        self.model.insert_search_results(word_indices_aggregated)
        self.model.mark_paths_unreachable(bad_path_ids)

        summary = SearchSummary(
            all_targets_already_searched=False,
            num_paths_searched=len(search_histories_aggregated),
            num_unreachable_paths=len(bad_path_ids),
            node_distribution=searchResults  # This includes the node distribution information
        )

        return summary


        # log_memory_and_disk_usage()
