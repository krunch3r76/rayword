# app/worker/wordsearch.py
# worker controller that finds matching words in list of resources and return results

import logging
from dataclasses import dataclass, asdict, field

from .model import WorkerIndexerModel
from .util.resource_loader import load_resource
from .util.word_in_context import find_all_words_details


# ----- logging --------------
# Suppress debug messages from urllib3 used by requests
logging.getLogger("urllib3").setLevel(logging.WARNING)
# Suppress debug messages from requests directly:
logging.getLogger("requests").setLevel(logging.WARNING)


@dataclass
class SearchHistory:
    word_id: int
    path_id: int

    def to_dict(self):
        return asdict(self)


@dataclass
class SearchResult:
    word_id: int
    path_id: int
    word_index: int
    sentence_indices: tuple
    paragraph_indices: tuple
    context_sentence: str
    context_paragraph: str
    sentence_index_start: int = field(init=False)
    sentence_index_end: int = field(init=False)
    paragraph_index_start: int = field(init=False)
    paragraph_index_end: int = field(init=False)

    def __post_init__(self):
        self.sentence_index_start = self.sentence_indices[0]
        self.sentence_index_end = self.sentence_indices[1] + 1
        self.paragraph_index_start = self.paragraph_indices[0]
        self.paragraph_index_end = self.paragraph_indices[1]

    def to_dict(self):
        # Exclude original indices tuples from the dictionary
        result_dict = asdict(self)
        del result_dict["sentence_indices"]
        del result_dict["paragraph_indices"]
        return result_dict


class WordSearcher:
    """
    A class responsible for searching words in given paths and aggregating results.

    This class processes word and path records, performs searches, and compiles the results.
    """

    def __init__(self, words_table, paths_table, path_prefix=None):
        """
        Initializes the WordSearcher with word and path records.

        Args:
            words_table (list): A list of word records to be searched.
            paths_table (list): A list of path records to be searched.
            path_prefix (str, optional): An optional prefix to be prepended to each path.
        """
        self.words_table = words_table
        self.paths_table = paths_table
        self.path_prefix = path_prefix
        self.workerModel = WorkerIndexerModel(words_table, paths_table, path_prefix)

    def perform_search(self):
        """
        Performs the word search operation and returns the results.

        Returns:
            dict: A dictionary containing search results and detailed history.
        """
        paths_searched, bad_path_ids = self.search_words_in_paths()

        # update search histories
        searchHistories = []
        for word_id in [
            wordRecord[0]
            for wordRecord in self.workerModel.select_records(
                "Words", ["word_id"], use_row_factory=False
            )
        ]:
            for path_id in paths_searched:
                searchHistories.append(SearchHistory(word_id=word_id, path_id=path_id))

        logging.debug(
            f"searched {len(paths_searched)} paths of which {len(bad_path_ids)} were unreachable"
        )
        self.workerModel.insert_records_into_worker_db(
            [searchHistory.to_dict() for searchHistory in searchHistories],
            "SearchHistory",
        )

        return self.create_search_result_dict(
            self.workerModel.select_records("WordIndices"),
            self.workerModel.select_records("SearchHistory"),
            bad_path_ids,
        )

    def search_words_in_paths(self):
        """
        Searches for words in each path and updates the model with the findings.

        Returns:
            tuple: A tuple containing lists of IDs of searched paths and IDs of paths where search failed.
        """
        bad_path_ids = set()
        paths_searched = []

        for path, path_id in self.workerModel.select_path_records(
            fields=["path", "path_id"]
        ):
            text, connection_timed_out = load_resource(path)
            if text:
                paths_searched.append(path_id)
                self.process_text_for_word_details(text, path_id)
            elif not connection_timed_out:
                bad_path_ids.add(path_id)

            if connection_timed_out:
                break

        return paths_searched, bad_path_ids

    def process_text_for_word_details(self, text, path_id):
        """
        Processes text to extract details of words and updates the model.

        Args:
            text (str): The text to be processed.
            path_id (int): The ID of the path from which the text is extracted.
        """
        words_list = [word_dict["word"] for word_dict in self.words_table]
        word_details = find_all_words_details(text, words_list)

        searchResults = []
        for word, word_index, sentence_indices, paragraph_indices in word_details:
            # find the word's associated word_id (can ask model to do this optimally instead?)
            word_id = self.workerModel.get_word_id(word)
            if word_id is None:
                raise ValueError(f"Word ID not found for word: {word}")
            context_sentence = text[sentence_indices[0] : sentence_indices[1]]
            context_paragraph = text[paragraph_indices[0] : paragraph_indices[1]]

            searchResults.append(
                SearchResult(
                    word_id=word_id,
                    path_id=path_id,
                    word_index=word_index,
                    sentence_indices=sentence_indices,
                    paragraph_indices=paragraph_indices,
                    context_sentence=context_sentence,
                    context_paragraph=context_paragraph,
                )
            )

        self.workerModel.insert_records_into_worker_db(
            [searchResult.to_dict() for searchResult in searchResults],
            "WordIndices",
        ),

    def create_search_result_dict(self, word_indices, search_histories, bad_path_ids):
        """
        Creates a dictionary of search outcomes to hand off to the caller.

        Args:
            word_indices (list): List of word indices found.
            paths_searched (list): List of IDs of paths successfully searched.
            bad_path_ids (list): List of IDs of paths that were not reachable.

        Returns:
            dict: A dictionary containing the search results.
        """
        return {
            "word_indices": word_indices,
            "search_histories": search_histories,
            # "searched_word_ids": [
            #     word_record["word_id"] for word_record in self.words_table
            # ],
            # "successfully_searched_path_ids": paths_searched,
            "unreachable_path_ids": bad_path_ids,
        }
