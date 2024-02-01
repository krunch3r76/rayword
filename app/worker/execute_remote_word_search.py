import ray
import logging


@ray.remote
def execute_remote_word_search(
    words_table, paths_table, path_prefix=None, enable_logging=False
):
    """
    Executes a search for words in the given paths, run as a Ray remote function.

    Args:
        words_table (list): List of dictionaries representing word records.
        paths_table (list): List of dictionaries representing path records.
        path_prefix (str, optional): Optional prefix for paths.

    Returns:
        Tuple[List[dict], Dict]: Tuple containing the search results and history information.
    """
    # logging.getLogger().setLevel(logging.WARNING)
    from .wordsearch import WordSearcher

    if enable_logging:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(filename)s:%(lineno)d - %(levelname)s - %(message)s",
        )

    word_searcher = WordSearcher(words_table, paths_table, path_prefix)
    return word_searcher.perform_search()
    # return perform_word_search(words_table, paths_table, path_prefix)
