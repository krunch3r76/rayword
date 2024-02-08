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

    def __call__(self, enable_console_logging=False):
        """
        Begins the process of distributing word search tasks.

        This method is the entry point for the word search operation. It retrieves
        unsearched paths for a given word and its internal set of related words
        and initiates the task distribution.

        Args:
            words: A list of words to be searched in the paths.
        """
        self.enable_console_logging = enable_console_logging
        unsearched_path_records = self.model.get_path_records()
        if len(unsearched_path_records) > 0:
            self.distribute_word_search_tasks(unsearched_path_records)
        else:
            print("All targets have been searched")

    def distribute_word_search_tasks(self, unsearched_paths):
        """
        Distributes word search tasks across a Ray cluster.

        This method generates tasks for each group of words and their associated unsearched paths.
        These tasks are then submitted to the Ray cluster for processing. The search results
        are aggregated and updated in the model.

        Args:
            words_to_unsearched_paths: A dictionary mapping words to their corresponding unsearched paths.

        Post:
            WordIndices table
            SearchHistory table
            Paths table (is_unreachable)
        """
        task_generator = TaskGenerator(batch_size=self.batch_size)
        task_submitter = TaskSubmitter(self.enable_console_logging)

        path_prefix = os.environ.get("RAYWORD_URL_PREFIX", None)
        print(f"searching {len(unsearched_paths)} texts")
        task_batches = task_generator.generate(unsearched_paths, path_prefix)

        searchResults = task_submitter.submit_and_process_tasks(task_batches)

        word_indices_aggregated, search_histories_aggregated, bad_path_ids = (
            [],
            [],
            set(),
        )

        for searchResult in searchResults:
            search_histories_aggregated.extend(searchResult["paths_searched"])
            word_positions_by_paths = searchResult["word_positions_by_paths"]
            for pathid, word_positions in word_positions_by_paths.items():
                # lookup textnumber
                text_number = self.model.lookup_text_number_by_path_id(pathid)
                for word, positions in word_positions.items():
                    for position in positions:
                        wordIndex = {
                            "word": word,
                            "word_index": position,
                            "text_number": text_number,
                        }
                        word_indices_aggregated.append(wordIndex)
                    # create WordIndices record
                    # add WordIndicesRecord
            bad_path_ids.update(searchResult["bad_paths"])

        self.model.insert_search_histories(search_histories_aggregated)
        self.model.insert_search_results(word_indices_aggregated)
        self.model.mark_paths_unreachable(bad_path_ids)
