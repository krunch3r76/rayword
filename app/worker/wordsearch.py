# app/worker/wordsearch.py
# worker controller that finds matching words in list of resources and return results
# from collections import namedtuple
import logging
import json
from dataclasses import dataclass, asdict

from .model import WorkerIndexerModel
from .util.resource_loader import load_resource
from .util.word_positions import find_all_words_positions

# SearchResult = namedtuple("SearchResult", ["path_id", "word_positions"])

# ----- logging --------------
# Suppress debug messages from urllib3 used by requests
logging.getLogger("urllib3").setLevel(logging.WARNING)
# Suppress debug messages from requests directly:
logging.getLogger("requests").setLevel(logging.WARNING)


@dataclass
class WordSearchResults:
    word_positions_by_paths: dict
    paths_searched: list
    bad_paths: list

    def to_json(self):
        return json.dumps(asdict(self))

    def to_dict(self):
        return asdict(self)


class WordSearcher:
    """
    A class responsible for searching tokenized words in given paths and aggregating results.
    """

    def __init__(self, paths_table, exclude_words=None, path_prefix=None):
        """
        Initializes the WordSearcher with word and path records.

        Args:
            paths_table (list): A list of path records to be searched.
            path_prefix (str, optional): An optional prefix to be prepended to each path.
        """
        if exclude_words is None:
            exclude_words = []
        self.exclude_words = exclude_words
        self.paths_table = paths_table
        self.path_prefix = path_prefix
        self.workerModel = WorkerIndexerModel(paths_table, path_prefix)
        self.path_id_to_results = (
            dict()
        )  # maps path to a dictionary of word to list of offsets
        self.paths_searched = []
        self.bad_path_ids = []

    def perform_search(self):
        """
        Performs the word search operation and returns the results.

        Returns:
            tuple of dict, list of paths searched, list bad paths: a dictionary mapping path_id to results that maps a word to its offsets
        """
        self.search_words_in_paths()

        # update search histories
        searchHistories = []

        for path_id in self.paths_searched:
            searchHistories.append(path_id)

        logging.debug(
            f"indexed {len(self.paths_searched)} paths of which {len(self.bad_path_ids)} {'was' if len(self.bad_path_ids) == 1 else 'were'} unreachable"
        )

        search_results = WordSearchResults(
            word_positions_by_paths=self.path_id_to_results,
            paths_searched=self.paths_searched,
            bad_paths=self.bad_path_ids,
        )

        return search_results

    def search_words_in_paths(self):
        """
        Searches for words in each path and updates the class with the findings.

        Post:
            self.paths_searched
            self.path_id_to_results
        """

        for path, path_id in self.workerModel.select_path_records(
            fields=["path", "path_id"]
        ):
            text, connection_timed_out = load_resource(path)
            if text:
                self.paths_searched.append(path_id)
                word_to_positions = find_all_words_positions(text, self.exclude_words)
                self.path_id_to_results[path_id] = word_to_positions
            elif not connection_timed_out:
                self.bad_path_ids.append(path_id)

            if connection_timed_out:
                logging.debug("connection timed out")
                continue
