# app/controller.py
from .task_submitter import TaskSubmitter
from .task_generator import TaskGenerator
import logging
import os


class Controller:
    """
    A controller class that orchestrates the word search process.

    This class takes a list of words, generates tasks for searching them in paths,
    submits these tasks to the Ray cluster, and processes the results.

    Attributes:
        model: The data model used for fetching and updating word and path records.
        view: An optional view component for displaying results (not implemented yet).
    """

    def __init__(self, model, batch_size, view=None):
        """
        Initializes the Controller with a model and an optional view.

        Args:
            model: The data model for accessing and updating records.
            view: An optional view component for displaying results (currently not implemented).
        """
        self.model = model
        self.view = view
        self.enable_console_logging = None
        self.batch_size = batch_size

    def __call__(self, word, enable_console_logging=False):
        """
        Begins the process of distributing word search tasks.

        This method is the entry point for the word search operation. It retrieves
        unsearched paths for a given word and its internal set of related words
        and initiates the task distribution.

        Args:
            words: A list of words to be searched in the paths.
        """
        self.enable_console_logging = enable_console_logging
        found_count = 0
        while found_count == 0:
            words_to_unsearched_paths = self.model.get_unsearched_paths_for_word_group(
                word
            )
            # review
            if len(words_to_unsearched_paths) > 0:
                found_count = self.distribute_word_search_tasks(
                    words_to_unsearched_paths
                )
            else:
                print("All targets have been searched already for this word")
                break
            if found_count == -1:
                print("All targets have been searched already for this word")
                break
            if found_count == 0:
                print("Word(s) not found, expanding search.")

    def distribute_word_search_tasks(self, words_to_unsearched_paths):
        """
        Distributes word search tasks across a Ray cluster.

        This method generates tasks for each group of words and their associated unsearched paths.
        These tasks are then submitted to the Ray cluster for processing. The search results
        are aggregated and updated in the model.

        Args:
            words_to_unsearched_paths: A dictionary mapping words to their corresponding unsearched paths.
        """
        task_generator = TaskGenerator(batch_size=self.batch_size)
        task_submitter = TaskSubmitter(self.enable_console_logging)

        path_prefix = os.environ.get("RAYWORD_URL_PREFIX", None)
        found_count = 0
        for words, path_records in words_to_unsearched_paths.items():
            print(f"searching {len(path_records)} texts")
            word_records = self.model.fetch_word_records(words)
            task_batches = task_generator.generate(
                word_records, path_records, path_prefix
            )

            (
                word_indices_aggregated,
                search_histories,
                summary,
            ) = task_submitter.submit_and_process_tasks(task_batches)

            # Update the model with search findings
            paths_reached = self.model.insert_search_histories(search_histories)
            if paths_reached > 0:
                self.model.mark_paths_unreachable(summary["bad_path_ids"])
                found_count += self.model.insert_search_results(word_indices_aggregated)
            else:
                found_count = -1

            # i am interested in the search histories that were just added (new to the model)
            # that correspond to the specific word provide (not related words)

        return found_count
