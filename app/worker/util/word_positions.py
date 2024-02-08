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


def _find_all_words_positions(text, exclude_words):
    """Index position of every word leveraging nltk RegexpTokenizer, excluding punctuation, words with numbers,
    single characters, specified words, and stripping leading and trailing underscores.

    Args:
        text (str): Text to tokenize.
        exclude_words (set): Set of words to exclude from adding to returned result.

    Returns:
        dictionary: Dictionary that maps a word to a list of offsets.
    """
    tokenizer = RegexpTokenizer(r"\w+(?:[-\']\w+)*")
    words = tokenizer.tokenize(text)

    word_dict = {}
    offset = 0

    for word in words:
        # Strip leading and trailing underscores and trailing possessive 's
        stripped_word = word.strip("_").rstrip("'s")
        normalized_word = stripped_word.lower()

        # Skip words in the exclusion list, words with digits, single characters, and blank words
        if (
            normalized_word in exclude_words
            or not normalized_word.isalpha()
            or len(normalized_word) <= 1
        ):
            offset += len(word)
            continue

        # Find the position of the cleaned word in the text
        current_offset = text.find(stripped_word, offset)

        # Check if the word was found and adjust the offset
        if current_offset != -1:
            word_dict.setdefault(normalized_word, []).append(current_offset)
            offset = current_offset + len(word)
        else:
            offset += len(word)

    return word_dict


def find_all_words_positions(text, exclude_words):
    """Index position of every word leveraging nltk RegexpTokenizer, excluding specified words.

    Args:
        text (str): Text to tokenize.
        exclude_words (set): Set of words to exclude from adding to returned result.

    Returns:
        dictionary: Dictionary that maps a word to a list of offsets.
    """
    tokenizer = RegexpTokenizer(r"\w+(?:[-\']\w+)*")
    exclude_words = set(word.lower() for word in exclude_words)

    word_dict = {}

    for start, end in tokenizer.span_tokenize(text):
        word = text[start:end]
        normalized_word = word.lower()

        # Skip words in the exclusion list, words with digits, single characters, and blank words
        if (
            normalized_word in exclude_words
            or not normalized_word.isalpha()
            or len(normalized_word) <= 1
        ):
            continue

        word_dict.setdefault(normalized_word, []).append(start)

    return word_dict
