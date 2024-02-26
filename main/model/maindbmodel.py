# main/model/maindbmodel.py
import logging
import json
import sqlite3

from .maindbconnection import create_main_db_connection
from .pathsdbconnection import create_paths_db_connection

logger = logging.getLogger()


class MainModel:
    def __init__(self, main_db_path, paths_db_path):
        """
        Args:
            main_db_path (str): Path to the main database file.
            paths_db_path (str): Path to the separate paths database file.
        """
        self.db_connection = create_main_db_connection(main_db_path, self)
        create_paths_db_connection(paths_db_path)
        self.attach_paths_db(paths_db_path)
        self.path_limit = None

    def attach_paths_db(self, paths_db_path):
        """
        Attach the paths database to the main database connection.

        Args:
            paths_db_path (str): Path to the paths database file.
        """
        attach_query = f"ATTACH DATABASE '{paths_db_path}' AS paths_db"
        self.db_connection.execute(attach_query)

    class CursorContextManager:
        """
        Context manager for managing database cursor.

        This context manager ensures that the database cursor is correctly opened
        and closed, and optionally manages the row_factory setting of the database
        connection for the duration of the context.

        Attributes:
            model (WorkerIndexerModel): The instance of the WorkerIndexerModel class.
            use_row_factory (bool): Flag to indicate whether to use a custom row factory.
        """

        def __init__(self, model, use_row_factory=False):
            self.model = model
            self.use_row_factory = use_row_factory
            self.original_row_factory = (
                model.words_db_connection.row_factory if use_row_factory else None
            )

        def __enter__(self):
            if self.use_row_factory:
                self.model.words_db_connection.row_factory = sqlite3.Row
            self.cursor = self.model.words_db_connection.cursor()
            return self.cursor

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.use_row_factory and self.original_row_factory is not None:
                self.model.words_db_connection.row_factory = self.original_row_factory
            self.cursor.close()
            # Handle exceptions if necessary
            if exc_type:
                # Log or handle the exception
                pass

    def lookup_path_for_text_number(self, text_number):
        """get the path field on Paths for a given text number"""
        with self.CursorContextManager(self, use_row_factory=False) as cursor:
            row = cursor.execute(
                "SELECT path FROM paths_db.Paths WHERE text_number = ?", (text_number,)
            ).fetchone()
            if row is not None:
                return row[0]
            else:
                return None

    def insert_search_histories(self, text_numbers, commit=False):
        """Insert text numbers into SearchHistory table.

        Args:
            text_numbers (list): List of text numbers to insert into SearchHistory.
        """
        insert_query = "INSERT INTO SearchHistory (text_number) VALUES (?)"
        with self.CursorContextManager(self) as cursor:
            # Insert each text number into the SearchHistory table
            cursor.executemany(
                insert_query, [(text_number,) for text_number in text_numbers]
            )
            if commit:
                self.db_connection.commit()

    def mark_texts_unreachable(self, path_strings):
        """Insert path_ids into UnreachablePaths table for given unreachable path strings.

        Args:
            path_strings (list): List of path strings corresponding to records in the Paths table.
        """
        insert_query = "INSERT OR IGNORE INTO UnreachablePaths (path_id) SELECT path_id FROM paths_db.Paths WHERE path = ?"
        with self.CursorContextManager(self) as cursor:
            # Insert each path_id into UnreachablePaths
            cursor.executemany(insert_query, [(path,) for path in path_strings])
            self.db_connection.commit()

    def lookup_word_by_word_id(self, word_id):
        """Return the word corresponding to the word_id"""
        with self.CursorContextManager(self, use_row_factory=False) as cursor:
            row = cursor.execute(
                "SELECT word from Words WHERE word_id = ?", (word_id,)
            ).fetchone()
            if row is None:
                raise Exception("no word for word id")
            return row[0]

    def get_word_id(self, word):
        """Return the word_id for a given word from the Words table."""
        with self.CursorContextManager(self) as cursor:
            cursor.execute("SELECT word_id FROM Words WHERE word = ?", (word,))
            result = cursor.fetchone()
            return result[0] if result else None

    def insert_word(self, word, commit=False):
        """Insert a new word into the Words table and return its word_id.

        Args:
            word (str): The word to insert.
            commit (bool): Whether to commit the transaction.

        Returns:
            int: The word_id of the inserted word.
        """
        with self.CursorContextManager(self) as cursor:
            cursor.execute("INSERT INTO Words (word) VALUES (?)", (word,))
            word_id = cursor.lastrowid
            if commit:
                self.db_connection.commit()
            return word_id

    def insert_into_word_indices(self, word_indices_data, commit=False):
        """Batch insert records into the WordIndices table.

        Args:
            word_indices_data (list of tuples): List of tuples where each tuple contains
                                                (word_id, word_index, text_number).
            commit (bool): Whether to commit the transaction.
        """
        with self.CursorContextManager(self) as cursor:
            cursor.executemany(
                "INSERT INTO WordIndices (word_id, word_index, text_number) VALUES (?, ?, ?)",
                word_indices_data,
            )
            if commit:
                self.db_connection.commit()

    def update_or_insert_paths(self, paths_and_text_numbers):
        """
        Inserts or updates path records in the attached Paths database.

        Args:
            paths_and_text_numbers (list): Tuples of paths (str) paired with the
                                            Gutenberg text number (int)

        Notes:
            Paths input and stored as the path component of a Gutenberg URL.
        """
        cursor = self.db_connection.cursor()

        number_of_unique_text_numbers_before_addition = cursor.execute(
            "SELECT COUNT(DISTINCT text_number) FROM paths_db.Paths"
        ).fetchone()[0]
        for path, text_number in paths_and_text_numbers:
            cursor.execute(
                "INSERT OR IGNORE INTO paths_db.Paths (path, text_number) VALUES (?, ?)",
                (path, text_number),
            )
        self.db_connection.commit()

        number_of_unique_text_numbers_after_addition = cursor.execute(
            "SELECT COUNT(DISTINCT text_number) FROM paths_db.Paths"
        ).fetchone()[0]

        return (
            number_of_unique_text_numbers_after_addition
            - number_of_unique_text_numbers_before_addition
        )

    def get_total_texts_and_unsearched_counts(self):
        """Return the total number of texts and the number of unsearched texts (that are reachable)."""
        with self.CursorContextManager(self, use_row_factory=True) as cursor:
            # Query to count total texts
            cursor.execute("SELECT COUNT(DISTINCT text_number) FROM paths_db.Paths")
            total_texts = cursor.fetchone()[0]

            # Query to count unsearched and reachable texts
            unsearched_query = """
                SELECT COUNT(DISTINCT p.text_number)
                FROM paths_db.Paths p
                LEFT JOIN SearchHistory sh ON p.text_number = sh.text_number
                LEFT JOIN UnreachablePaths up ON p.path_id = up.path_id
                WHERE sh.text_number IS NULL AND up.path_id IS NULL
                """
            cursor.execute(unsearched_query)
            unsearched_count = cursor.fetchone()[0]

        return total_texts, unsearched_count

    def get_unsearched_path_records(self, max_paths=None, to_json=False):
        """
        Retrieve a specified number of Path records for which there is no corresponding text_number match
        in SearchHistory and not listed in UnreachablePaths, returned in random order.

        Args:
            max_paths (int or None): Maximum number of paths to retrieve. If None, no limit is applied.
            to_json (bool): If True, returns results as a JSON string.

        Returns:
            List of dictionaries or JSON string of path records.
        """
        if max_paths is None:
            max_paths = self.path_limit

        with self.CursorContextManager(self, use_row_factory=True) as cursor:
            # SQL query to find the required Path records
            query = """
            SELECT p.path_id, p.path, p.text_number
            FROM paths_db.Paths p
            LEFT JOIN SearchHistory sh ON p.text_number = sh.text_number
            LEFT JOIN UnreachablePaths up ON p.path_id = up.path_id
            WHERE sh.text_number IS NULL AND up.path_id IS NULL
            ORDER BY RANDOM()
            """

            # Limit the number of paths if max_paths is specified
            if max_paths:
                query += f" LIMIT {max_paths}"

            cursor.execute(query)
            # Fetch all matching records as a list of dictionaries
            results = [dict(row) for row in cursor.fetchall()]

            # Convert the results to JSON if required
            if to_json:
                return json.dumps(results)

            return results

    def _build_word_to_word_id_dict(self, wordlist):
        word_to_word_id = dict()
        with self.CursorContextManager(self, use_row_factory=True) as cursor:
            for word in wordlist:
                row = cursor.execute(
                    "SELECT word_id FROM Words where word = ?", (word,)
                ).fetchone()
                if row is None:
                    # add word
                    word_id = self.insert_word(word, commit=True)
                else:
                    word_id = row[0]

                word_to_word_id[word] = word_id
        return word_to_word_id

    def _build_word_id_to_count_dict(self, word_to_word_id):
        def __count_word_indices_records_for_word_id(word_id):
            with self.CursorContextManager(self, use_row_factory=True) as cursor:
                count = cursor.execute(
                    "SELECT COUNT(*) from WordIndices where word_id = ?", (word_id,)
                ).fetchone()[0]
                return count

        word_id_list = [word_id for word_id in word_to_word_id.values()]
        word_id_to_indices_count = dict()
        for word_id in word_id_list:
            indices_count_for_word_id = __count_word_indices_records_for_word_id(
                word_id
            )
            word_id_to_indices_count[word_id] = indices_count_for_word_id
        return word_id_to_indices_count

    def count_instances_of_words(self, wordlist, primary_word):
        word_to_word_id = self._build_word_to_word_id_dict(wordlist)
        word_id_to_count = self._build_word_id_to_count_dict(word_to_word_id)
        primary_word_count = word_id_to_count[word_to_word_id[primary_word]]
        total_count = sum([count for count in word_id_to_count.values()])
        non_primary_word_count = total_count - primary_word_count
        return primary_word_count, non_primary_word_count

    def random_word_index_record(
        self, wordlist, primary_word, exclude_ids=None, prefer_primary=True
    ):
        """get a random WordIndex record corresponding to the word with optional preference
        to the primary word or return None"""

        def __randomly_select_index_record_given_word_id(word_id, exclude_ids):
            with self.CursorContextManager(self, use_row_factory=True) as cursor:
                records = cursor.execute(
                    "SELECT * FROM WordIndices WHERE word_id = ? ORDER BY RANDOM()",
                    (word_id,),
                ).fetchall()
                wordIndexRecord = None
                for record in records:
                    wordIndexRecord_candidate = dict(record)
                    if wordIndexRecord_candidate["word_indices_id"] in exclude_ids:
                        continue
                    wordIndexRecord = wordIndexRecord_candidate
                    break

                return wordIndexRecord

        if exclude_ids is None:
            exclude_ids = []

        word_to_word_id = self._build_word_to_word_id_dict(wordlist)
        word_id_to_count = self._build_word_id_to_count_dict(word_to_word_id)
        logging.debug(word_id_to_count)
        primary_word_count = 0
        word_id_to_search_for = None
        random_record = None
        if prefer_primary:
            primary_word_id = word_to_word_id[primary_word]
            primary_word_count = word_id_to_count[primary_word_id]
            if primary_word_count > 0:  # review
                word_id_to_search_for = primary_word_id
                random_record = __randomly_select_index_record_given_word_id(
                    word_id_to_search_for, exclude_ids=exclude_ids
                )

        excluded_count = 0
        if random_record is None:
            excluded_count = primary_word_count
        max_count = sum([count for count in word_id_to_count.values()])
        while excluded_count < max_count:
            for word_id, count in word_id_to_count.items():
                if count > 0:
                    word_id_to_search_for = word_id
                random_record = __randomly_select_index_record_given_word_id(
                    word_id_to_search_for, exclude_ids=exclude_ids
                )
                if random_record is not None:
                    return random_record
                else:
                    excluded_count += 1

        return random_record
