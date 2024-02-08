# app/task_generator.py
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging


@dataclass
class Task:
    """
    Data class representing a single task for word search processing.

    This class encapsulates all necessary information to perform a word search task,
    including the word records, path records, and their corresponding IDs, along with
    an optional path prefix.

    Attributes:
        word_records (List[dict]): A list of word record dictionaries.
        path_records (List[dict]): A list of path record dictionaries.
        word_id_path_id_pairs (List[Tuple[int, int]]): A list of tuples where each tuple
                                                       contains a word ID and a corresponding path ID.
        path_prefix (Optional[str]): An optional string to be prefixed to each path, if provided.
    """

    path_records: List[dict]
    path_prefix: Optional[str] = None


class TaskGenerator:
    """
    A generator for creating batches of tasks to be processed for word searches.

    The TaskGenerator is responsible for dividing a large set of path records into smaller
    batchesforming tasks that are ready for further processing.

    Attributes:
        batch_size (int): The number of path records to include in each batch.
    """

    def __init__(self, batch_size):
        """
        Initializes the TaskGenerator with a specified batch size.

        Args:
            batch_size (int): The number of path records to be included in each task batch.
        """
        self.batch_size = batch_size

    def generate(self, path_records, path_prefix=None):
        """
        Generates batches of tasks from the provided path records.

        Iterates over path records, grouping them into batches.

        Args:
            path_records (List[dict]): The path records to be searched.
            path_prefix (Optional[str]): Optional prefix for paths.

        Yields:
            Task: A Task object representing a batch of work to be processed.
        """
        logging.debug(f"Path records count: {len(path_records)}")
        logging.debug(f"Batch size: {self.batch_size}")

        max_range = max(len(path_records), self.batch_size)

        for i in range(0, max_range, self.batch_size):
            batch = path_records[i : min(i + self.batch_size, len(path_records))]
            task = Task(batch, path_prefix)
            logging.debug(f"Generated task with {len(batch)} path records.")
            yield task
