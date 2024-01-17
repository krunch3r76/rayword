# worker/util/word_in_context.py

import re
import os
import nltk

from nltk.tokenize import sent_tokenize

# Current script's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Navigate up one level to get the worker directory
worker_dir = os.path.dirname(current_dir)
# Construct the nltk_data path
nltk_data_path = os.path.join(worker_dir, "nltk_data")
nltk.data.path.append(nltk_data_path)


def find_all_words_details(text, target_words):
    # Precompile the regex pattern outside the loop
    escaped_words = [re.escape(word) for word in target_words]
    pattern = re.compile(rf"\b({'|'.join(escaped_words)})\b", re.IGNORECASE)

    word_details = []

    # Splitting the text into paragraphs
    paragraphs = re.split(r"\n\s*\n", text.strip())

    # Track the current index in the text
    current_index = 0

    # Iterate through each paragraph
    for paragraph in paragraphs:
        paragraph_start = text.find(paragraph, current_index)
        paragraph_end = paragraph_start + len(paragraph)
        current_index = paragraph_end

        # Iterate through sentences within the paragraph
        for sentence in sent_tokenize(paragraph):
            sentence_start = text.find(sentence, paragraph_start)
            sentence_end = sentence_start + len(sentence)

            # Find all occurrences of the target words within the sentence
            for match in pattern.finditer(sentence):
                word_offset = sentence_start + match.start()

                word_details.append(
                    (
                        match[0].lower(),
                        word_offset,
                        (sentence_start, sentence_end),
                        (paragraph_start, paragraph_end),
                    )
                )

    return word_details


if __name__ == "__main__":
    import sys
    import zipfile

    def _print_context(text, word_details):
        word, word_index, sentence_indices, paragraph_indices = word_details

        # Extract and print the sentence
        input("enter to see sentence containing the word")
        sentence = text[sentence_indices[0] : sentence_indices[1]]
        print("Sentence containing the word:")
        print(sentence)
        print("\n\n")

        input("enter to see paragraph containing the word")
        # Extract and print the paragraph
        paragraph = text[paragraph_indices[0] : paragraph_indices[1]]
        print("\nParagraph containing the sentence:")
        print(paragraph)
        print("\n\n")

    if len(sys.argv) < 3:
        print("usage: {sys.argv[0]} <zipped text file> <words>")
        sys.exit(1)
    zipfilepath = sys.argv[1]
    words_to_find = sys.argv[2:]
    text_content = None
    with zipfile.ZipFile(zipfilepath, "r") as zip_ref:
        # text_content = zip_ref.read(zip_ref.namelist()[0]).decode("utf-8")
        text_content_binary = zip_ref.read(zip_ref.namelist()[0])
        text_content = text_content_binary.decode("iso-8859-1")

    results = find_all_words_details(text_content, words_to_find)
    # print(f"Word Index: {result[0]}")
    # print(f"Sentence Indices: {result[1]}")
    # print(f"Paragraph Indices: {result[2]}")

    for result in results:
        _print_context(text_content, result)

    print(f"result count: {len(results)}, pless enter")
