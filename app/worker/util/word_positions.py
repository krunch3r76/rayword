# worker/util/word_in_context.py

# nltk.download('punkt')
import nltk
from pathlib import Path
from nltk.tokenize import word_tokenize
import string

worker_dir = Path(__file__).parent.parent
nltk_data_path = worker_dir / "nltk_data"
nltk.data.path.append(str(nltk_data_path))
from nltk.tokenize import RegexpTokenizer
from sys import intern


def find_all_words_positions(worker_indexer_model, text, exclude_words, path_id):
    """Index position of every word leveraging nltk RegexpTokenizer, excluding specified words,
    and inserts them into a database using WorkerIndexerModel.

    Args:
        worker_indexer_model (WorkerIndexerModel): The WorkerIndexerModel instance for DB operations.
        text (str): Text to tokenize.
        exclude_words (set): Set of words to exclude from adding to returned result.
        path_id (int): The identifier of the path or text being processed.
    """
    tokenizer = RegexpTokenizer(r"\w+(?:[-\']\w+)*")
    exclude_words = set(intern(word.lower()) for word in exclude_words)

    for start, end in tokenizer.span_tokenize(text):
        word = text[start:end]
        normalized_word = intern(word.lower())

        # Skip words in the exclusion list, words with digits, single characters, and blank words
        if (
            normalized_word in exclude_words
            or not normalized_word.isalpha()
            or len(normalized_word) <= 1
        ):
            continue

        # Insert the word into the Words table and get the word_id
        word_id = worker_indexer_model.insert_word(normalized_word)

        # Insert the position into the Positions table
        worker_indexer_model.insert_word_position(word_id, path_id, start)
