# wordbrowser/gutenberg_extractor.py

import logging

import os


def extract_title_and_authors(file_path, text_number):
    """
    Extract title and authors for the given text number from the Project Gutenberg index file.

    Args:
        file_path (str): The path to the Project Gutenberg index file.
        text_number (int): The text number of the eBook to search for.

    Returns:
        tuple: A tuple containing the title and authors.
    """
    if not os.path.exists(file_path):
        return "File not found", "File not found"

    with open(file_path, "r", encoding="utf-8") as file:
        content = file.readlines()

    title = None
    authors = None

    for line in content:
        if str(text_number) in line:
            parts = line.split("by")
            title = parts[0].strip()

            if len(parts) > 1:
                author_part = parts[1].rsplit(str(text_number), 1)[0].strip()
                author_part = author_part.rstrip("C").strip()
                authors = author_part
            else:
                authors = "Unknown Author"
            break

    if not title:
        title = "Title not found"
    if not authors:
        authors = "Authors not found"

    return title, authors
