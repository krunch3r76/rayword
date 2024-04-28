import ray
import logging


# runtime_env = {"pip": ["requests", "nltk"]}
# ray.init(runtime_env=runtime_env)


@ray.remote
def execute_remote_word_search(paths_table, path_prefix=None, enable_logging=False):
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

    exclusions = {
        "a",
        "about",
        "above",
        "across",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "beneath",
        "beside",
        "between",
        "beyond",
        "both",
        "but",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "either",
        "enough",
        "even",
        "ever",
        "every",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "just",
        "like",
        "me",
        "might",
        "mine",
        "more",
        "most",
        "much",
        "must",
        "my",
        "myself",
        "neither",
        "no",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "since",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "toward",
        "towards",
        "under",
        "until",
        "up",
        "upon",
        "us",
        "used",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
    word_searcher = WordSearcher(
        paths_table, path_prefix=path_prefix, exclude_words=exclusions
    )
    word_search_results = word_searcher.perform_search()
    return word_search_results.to_compressed_json()

    # return perform_word_search(words_table, paths_table, path_prefix)
