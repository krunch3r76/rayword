#!/usr/bin/env python3
# wordbrowser/browse.py
# browse main model for word instances
import sys
from pathlib import Path
import argparse
import logging
import os

project_root_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root_dir))
from main.model.maindbmodel import MainModel
from app.worker.util.resource_loader import load_resource

import nltk
from nltk.tokenize import sent_tokenize

nltk_data_path = project_root_dir / "app" / "worker" / "nltk_data"
nltk.data.path.append(str(nltk_data_path))


def find_word_forms(word):
    """leverage nltk (if available) to find all the forms of the word being searched

    Args:
        word: the word searched for

    Returns:
        list (str): the word searched for and other forms (if any) found
    """
    try:
        import nltk

        nltk_data_dir = Path(__file__) / "nltk_data"
        nltk.data.path.append(str(nltk_data_dir))
        from word_forms.word_forms import get_word_forms
    except (NameError, ModuleNotFoundError):
        return [word]
    else:
        word_forms_data = get_word_forms(word)
        combined_set = set()
        for forms in word_forms_data.values():
            combined_set.update(forms)
        if len(combined_set) == 0:
            combined_set.add(word)
        return list(combined_set)


def construct_url_from_path(path, path_prefix="http://aleph.gutenberg.org"):
    import os

    if "RAYWORD_URL_PREFIX" in os.environ:
        path_prefix = os.environ["RAYWORD_URL_PREFIX"]
    return path_prefix + path


def extract_sentence_with_context(text, word_offset):
    """
    Extracts the sentence containing the word at the given offset.

    Args:
        text (str): The full text.
        word_offset (int): The character offset of the word in the text.

    Returns:
        str: The sentence containing the word, or 'Sentence not found.' if not found.
    """
    sentences = sent_tokenize(text)
    current_index = 0

    for sentence in sentences:
        sentence_start = text.find(sentence, current_index)
        sentence_end = sentence_start + len(sentence)

        # Check if the word offset is within the current sentence
        if sentence_start <= word_offset < sentence_end:
            return sentence

        current_index = sentence_end

    return "Sentence not found."


if __name__ == "__main__":
    # Setup logging
    log_level = "DEBUG" if "KRUNCHDEBUG" in os.environ else "WARNING"
    logging.basicConfig(
        level=log_level,
        format="%(filename)s[line:%(lineno)d] - %(levelname)s - %(message)s",
    )
    parser = argparse.ArgumentParser(description="Browse rayword search results")
    parser.add_argument("word", help="The primary word for which to look")
    args = parser.parse_args()

    mainModel = MainModel("../data/main.db", "../data/paths.db")
    (
        total_texts_count,
        unsearched_count,
    ) = mainModel.get_total_texts_and_unsearched_counts()
    print(
        f"out of a total of {total_texts_count} texts, {total_texts_count - unsearched_count} texts have been indexed."
    )

    try:
        import nltk
    except ModuleNotFoundError:
        print("nltk has not been installed into this python environment")
        print("please run `pip3 install nltk and retry")

    try:
        import word_forms
    except ModuleNotFoundError:
        print("word_forms package has not been installed into this python environment")
        print("please run `pip3 install word_forms` and retry")

    wordlist = find_word_forms(args.word)

    print(
        f"searching for instances of {', '.join([word for word in wordlist])} while preferring {args.word}"
    )

    primary_word_count, non_primary_word_count = mainModel.count_instances_of_words(
        wordlist, args.word
    )
    print(
        f"there are {primary_word_count} instances of {args.word} and {non_primary_word_count} instances of any other related word forms"
    )

    if primary_word_count + non_primary_word_count == 0:
        sys.exit(0)

    exclusion_ids = []
    random_word_index_record = mainModel.random_word_index_record(
        wordlist, args.word, exclusion_ids
    )
    while len(exclusion_ids) < primary_word_count + non_primary_word_count:
        logging.debug(random_word_index_record)

        path = mainModel.lookup_path_for_text_number(
            random_word_index_record["text_number"]
        )

        url = construct_url_from_path(path)
        text, _ = load_resource(url)
        offset = random_word_index_record["word_index"]
        # print(text[random_word_index_record["word_index"]:random
        word_chosen = mainModel.lookup_word_by_word_id(
            random_word_index_record["word_id"]
        )
        # print(text[offset - 255 : offset + len(word_chosen) + 0])
        context_sentence = extract_sentence_with_context(text, offset)
        print("\n\n")
        print(context_sentence)
        print("\n\n")
        exclusion_ids.append(random_word_index_record["word_indices_id"])
        if len(exclusion_ids) < primary_word_count + non_primary_word_count:
            logging.debug(f"{exclusion_ids}: len->{len(exclusion_ids)}")
            input(f"press enter for next one")
            random_word_index_record = mainModel.random_word_index_record(
                wordlist, args.word, exclusion_ids
            )
        else:
            input("that's all folks: no more quotes. enter to exit")
