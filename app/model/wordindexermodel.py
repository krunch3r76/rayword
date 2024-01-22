# app/model/wordindexermodel.py
"""
WordIndexerModel Module

This module defines the WordIndexerModel class for the WordIndexer application. 
It provides a CRUD (Create, Read, Update, Delete) interface for managing words, paths, 
and search histories in associated SQLite database(s). The class handles database connections 
and includes methods for updating path records, fetching word records, and serializing data for 
remote nodes.

Dependencies: 
- SQLite3 for database management.
- Logging for debugging and error logging.

Created by krunch3r76 on 12-28-2023
"""
import logging
import json
import sqlite3

from .wordsdbconnection import create_words_db_connection
from constants import WORDS_DB_FILE

# from .contextdbconnection import create_context_db_connection

logger = logging.getLogger()


class WordIndexerModel:
    """
    A persistent model for indexing and storing paths and word search histories.

    Provides serialization methods for sharing relevant data to remote nodes.

    Attributes:
        words_db_connection (sqlite3.connection):
        path_limit (int): upper count of paths to return when querying unsearched
    """

    # (attribute) words_db_connection
    def __init__(
        self, words_db_path=str(WORDS_DB_FILE), context_db_path=None, path_limit=None
    ):
        """
        Args:
            words_db_path (stringable): path to on disk sqlite words database (created if non existent)
            context_db_path (stringable): deprecated, path to context database
            path_limit (int): max number of path's returned by unsearched paths query
        """
        # Create the primary connection (e.g., words database)
        self.words_db_connection = create_words_db_connection(words_db_path, self)
        self.path_limit = path_limit
        # # Create a secondary connection (e.g., context database)
        # # And optionally, if you need to perform cross-database queries:
        # self.context_db_connection = create_context_db_connection(context_db_path)
        # self._attach_context_db(self.context_db_connection)

    # deprecated
    # def _attach_context_db(self, context_conn):
    #     # Use the ATTACH DATABASE command to attach context database to words database
    #     context_db_path = context_conn.execute("PRAGMA database_list").fetchone()[2]
    #     self.words_db_connection.execute(
    #         f"ATTACH DATABASE '{context_db_path}' AS contextDb"
    #     )

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

    def get_random_word_index_above_id(self, last_processed_id, words):
        """
        Fetches a random WordIndices row where word_indices_id is greater than last_processed_id
        and the word matches one of the specified words in the Words table.

        Args:
            last_processed_id (int): The word_indices_id threshold.
            words (list of str): The words to match in the Words table.

        Returns:
            dict: A dictionary representing the selected row from WordIndices.
        """
        if not isinstance(words, list):
            words = [words]

        with self.cursor_context(use_row_factory=True) as cursor:
            placeholders = ",".join("?" * len(words))
            query = f"""
                    SELECT wi.*
                    FROM WordIndices wi
                    JOIN Words w ON wi.word_id = w.word_id
                    WHERE wi.word_indices_id > ?
                    AND w.word IN ({placeholders})
                    ORDER BY RANDOM()
                    LIMIT 1;
                    """
            cursor.execute(query, (last_processed_id, *words))

            result = cursor.fetchone()
            return dict(result) if result else None

    def cursor_context(self, use_row_factory=False):
        return WordIndexerModel.CursorContextManager(
            model=self, use_row_factory=use_row_factory
        )

    def get_history_index_range(self):
        """return the inclusive range of row_id's corresponding to the most recent records added"""
        with self.cursor_context() as cursor:
            try:
                # Execute the query
                cursor.execute(
                    "SELECT penultimate_max_index_id, ultimate_max_index_id FROM History"
                )
                result = cursor.fetchone()

                # Check if the result is not None
                if result is not None:
                    return result  # Returns a tuple (penultimate_max_index_id, ultimate_max_index_id)
                else:
                    return None  # or some default value or raise an exception

            except sqlite3.Error as e:
                print(f"An error occurred: {e}")
                return None  # or some default value or raise an exception

    def get_count_records_last_added(self):
        """return the number of records most recently added"""
        index_range = self.get_history_index_range()
        if index_range is None:
            max_index = self.get_max_word_indices_id()
            return max_index
        return index_range[1] - index_range[0]

    def update_insertion_history(self):
        """
        Updates the insertion history in the History table with the latest word index ID.

        Retrieves the current maximum word index ID and updates the History table by
        setting this as the new ultimate maximum ID and the previous ID as the penultimate maximum ID.
        If no record exists, inserts a new one. Logs the historical and new maximum IDs for debugging.

        Returns:
            int: -1 if no prior history exists, 0 if no new insertions, or the number of new insertions since the last update.
        """
        try:
            new_max_id = self.get_max_word_indices_id()
            with self.cursor_context() as cursor:
                # Fetch the current ultimate_max_index_id
                cursor.execute("SELECT ultimate_max_index_id FROM History")
                result = cursor.fetchone()
                if result is None:
                    cursor.execute(
                        "INSERT OR REPLACE INTO History (id, ultimate_max_index_id, penultimate_max_index_id) VALUES (1, ?, ?)",
                        (new_max_id, new_max_id),
                    )
                    self.words_db_connection.commit()
                    return -1

                historical_max_id = result[0]
                logging.debug(
                    f"HISTORICAL_MAX_ID: {historical_max_id}, NEW_MAX_ID: {new_max_id}"
                )
                if new_max_id == historical_max_id:
                    # no new records, can return
                    return 0

                cursor.execute(
                    "INSERT OR REPLACE INTO History (id, ultimate_max_index_id, penultimate_max_index_id) VALUES (1, ?, ?)",
                    (new_max_id, historical_max_id),
                )

            # Commit the transaction
            self.words_db_connection.commit()
            return new_max_id - historical_max_id

        except Exception as e:
            # Handle exceptions
            logging.error(f"An error occurred: {e}")
            # Rollback any changes made before the exception
            self.words_db_connection.rollback()
            raise

    def get_max_word_indices_id(self):
        """
        Performs a sql query to identify the most recent inserted record.
        """
        with self.cursor_context() as cursor:
            cursor.execute("SELECT MAX(word_indices_id) FROM WordIndices")
            max_id = cursor.fetchone()[0]

        if max_id is not None:
            return max_id
        else:
            return 0

    # def select_random_word_indices_record(
    def update_or_insert_paths(self, paths_and_text_numbers):
        """
        Inserts or updates path records

        Args:
            paths_and_text_numbers (list): tuples of paths (str) paired with the
             gutenberg text number (int)

        Notes:
            paths input and stored as the path component of a gutenberg url
        """
        cursor = self.words_db_connection.cursor()

        for path, text_number in paths_and_text_numbers:
            cursor.execute(
                "INSERT OR IGNORE INTO Paths (path, text_number) VALUES (?, ?)",
                (path, text_number),
            )
        self.words_db_connection.commit()

    def mark_paths_unreachable(self, path_ids):
        """
        Sets is_invalid to 1 on the records corresponding to path_ids

        Args:
            path_ids (list): list of path ids corresponding to primary key on Paths tables
        """
        update_query = "UPDATE Paths SET is_unreachable = 1 WHERE path_id = ?"
        cursor = self._cursor()
        cursor.executemany(update_query, [(path_id,) for path_id in path_ids])
        self.words_db_connection.commit()

    def fetch_word_records(self, words):
        """
        Retrieves a list Words records for the words in the input group

        Args:
            words (list of str): words to look up the corresponding Words records

        Returns:
            list of dict: a list of dictionaries containing complete Words records
        """
        original_row_factory = self.words_db_connection.row_factory
        self.words_db_connection.row_factory = sqlite3.Row
        cursor = self._cursor()
        placeholders = ", ".join("?" for _ in words)
        cursor.execute(f"SELECT * FROM Words WHERE word IN ({placeholders})", words)
        word_records = cursor.fetchall()
        self.words_db_connection.row_factory = original_row_factory
        return [dict(record) for record in word_records]

    def fetch_selected_path_records(self, path_ids):
        """
        Retrieves a list of Paths records corresponding to the path_ids

        Args:
            path_ids (list of int): existing path_ids to filter against

        Returns:
            list of dict: a list of dictionaries containing the complete Paths records
        """
        MAX_SQLITE_PARAMETERS = 999

        # setup cursor for Row factory
        original_row_factory = self.words_db_connection.row_factory
        self.words_db_connection.row_factory = sqlite3.Row
        cursor = self._cursor()

        def fetch_chunk(ids_chunk):
            placeholders = ",".join("?" for _ in ids_chunk)
            cursor.execute(
                f"SELECT * FROM Paths WHERE path_id IN ({placeholders})", ids_chunk
            )
            return [dict(row) for row in cursor.fetchall()]

        # Split path_ids into chunks and fetch records for each chunk
        records = []
        for i in range(0, len(path_ids), MAX_SQLITE_PARAMETERS):
            chunk = path_ids[i : i + MAX_SQLITE_PARAMETERS]
            records.extend(fetch_chunk(chunk))

        self.words_db_connection.row_factory = original_row_factory

        return records

    def update_or_insert_word_groups(self, word_list):
        """
        Inserts or updates a grouping of words by creating or associating a FormGroup record

        Args:
            word_list (list of str): words to be recognized as part of the single group
        """
        cursor = self.words_db_connection.cursor()

        for word in word_list:
            # Check if the word already exists
            cursor.execute(
                "SELECT word_id, form_group_id FROM Words WHERE word = ?", (word,)
            )
            result = cursor.fetchone()

            if result:
                # Word exists, fetch its form_group_id
                word_id, form_group_id = result
            else:
                # Word doesn't exist, create new FormGroup
                cursor.execute("INSERT INTO FormGroups DEFAULT VALUES")
                form_group_id = cursor.lastrowid

                # Add all words in the list to Words with the new form_group_id
                for w in word_list:
                    cursor.execute(
                        "INSERT INTO Words (word, form_group_id) VALUES (?, ?)",
                        (w, form_group_id),
                    )

            # If the word exists, update other words in the same group if necessary
            if result:
                cursor.execute(
                    "SELECT word FROM Words WHERE form_group_id = ?", (form_group_id,)
                )
                existing_words = {row[0] for row in cursor.fetchall()}
                new_words = set(word_list) - existing_words

                for w in new_words:
                    cursor.execute(
                        "INSERT INTO Words (word, form_group_id) VALUES (?, ?)",
                        (w, form_group_id),
                    )
            self.words_db_connection.commit()

    def _cursor(self):
        """
        Creates and returns a new cursor object from the database connection.

        Returns:
            sqlite3.Cursor: A new cursor object for the database.
        """
        return self.words_db_connection.cursor()

    def serialize_selected_words_to_json(self, word_list):
        """
        Serializes Words records corresponding to the word_list as json records

        Args:
            word_list (list of str): words to look up corresponding Words records

        Returns:
            str: json list of dictionaries corresponding to Words records
        """

        def convert_words_to_ids(word_list):
            """
            Returns word_ids corresponding to the word_list

            Args:
                word_list (list of str): words to search for in Words

            Returns:
                list of int: word_id's from Words
            """
            placeholders = ", ".join("?" for _ in word_list)
            query = "SELECT word_id from Words WHERE word IN ({})".format(placeholders)
            logger.debug(query)
            cursor = self._cursor()
            cursor.execute(query, word_list)
            word_ids_rows = cursor.fetchall()
            word_ids = [row[0] for row in word_ids_rows]
            return word_ids

        original_row_factory = self.words_db_connection.row_factory
        self.words_db_connection.row_factory = sqlite3.Row
        cursor = self._cursor()

        word_ids = convert_words_to_ids(word_list)
        placeholders = ", ".join("?" for _ in word_list)
        query = f"SELECT word_id, word, form_group_id FROM Words WHERE word_id IN ({placeholders})"
        cursor.execute(query, word_ids)
        fetched = cursor.fetchall()
        words_data = [dict(row) for row in fetched]
        self.words_db_connection = original_row_factory
        json_data = json.dumps(words_data)
        return json_data

    # def _compress_to_base64(self, text):
    #     compressed_text = gzip.compress(text.encode("utf-8"))
    #     base64_compressed_text = base64.b64encode(compressed_text).decode("utf-8")
    #     return base64_compressed_text

    def get_unsearched_path_ids_for_word_group(self, word):
        """
        Collates words with shared paths for which the words have not yet been searched on.

        Args:
            word (str): a representative word of the group to which it may belong

        Returns:
            dictionary of tuples to lists: keys are tuples of words associated with a list of
                path_ids from Paths
        """

        # setup cursor for Row factory
        original_row_factory = self.words_db_connection.row_factory
        self.words_db_connection.row_factory = sqlite3.Row
        cursor = self._cursor()

        # Combined query to get word_ids and words for a given group
        query = """
        SELECT w1.word_id, w1.word
        FROM Words w1
        JOIN Words w2 ON w1.form_group_id = w2.form_group_id
        WHERE w2.word = ?
        """
        cursor.execute(query, (word,))
        word_ids_and_words = cursor.fetchall()

        # Function to get unsearched path IDs for a given word_id
        def unsearched_path_ids_for_word_id(word_id, randomorder=True):
            limit_clause = (
                f"LIMIT {self.path_limit}" if self.path_limit is not None else ""
            )
            order_by_clause = "ORDER BY RANDOM()" if randomorder else "ORDER BY path_id"
            query = f"""
            SELECT path_id
            FROM Paths
            WHERE path_id NOT IN (
                SELECT path_id
                FROM SearchHistory
                WHERE word_id = ?
            )
            AND is_unreachable = 0
            {order_by_clause} {limit_clause}
            """
            cursor.execute(query, (word_id,))
            return [row[0] for row in cursor.fetchall()]

        # Building the mapping
        unsearched_paths_to_words = {}
        for word_id, word in word_ids_and_words:
            path_ids = tuple(unsearched_path_ids_for_word_id(word_id))
            if path_ids not in unsearched_paths_to_words:
                unsearched_paths_to_words[path_ids] = []
            unsearched_paths_to_words[path_ids].append(word)

        self.words_db_connection.row_factory = original_row_factory

        # Invert the mapping to map the lists of words to distinct lists of search paths
        return {
            tuple(words): paths for paths, words in unsearched_paths_to_words.items()
        }

    def get_unsearched_paths_for_word_group(self, word):
        """collate words with unsearched path ids

        Args:
            word (str): a word expected to be a sampling from the group it belongs to

        Returns:
            one or more lists of words keyed to unsearched paths
        """
        word_groups_to_path_ids = self.get_unsearched_path_ids_for_word_group(word)
        wordlists_to_paths = {}
        for wordlist, path_ids in word_groups_to_path_ids.items():
            path_records = self.fetch_selected_path_records(path_ids)
            wordlists_to_paths[wordlist] = path_records
        return wordlists_to_paths

    def insert_search_histories(self, searchHistories):
        """update the model with what paths were searched for the words

        Args:
            word_id_to_path_id_pairs (list): tuples of individual word ids associated to path ids
        """
        if len(searchHistories) != 0:
            cursor = self._cursor()

            columns = ", ".join(searchHistories[0].keys())
            placeholders = ":" + ", :".join(searchHistories[0].keys())
            sql = f"INSERT INTO SearchHistory ({columns}) VALUES ({placeholders})"
            cursor.executemany(sql, searchHistories)
            self.words_db_connection.commit()

        return len(searchHistories)

    def insert_search_results(self, wordIndices_list):
        """update the model with word search results

        Args:
            wordIndices_list (list): dictionary objects serving as records for the model to insert
        """
        logger.debug(f"inserting {len(wordIndices_list)} records")
        if len(wordIndices_list) > 0:
            cursor = self._cursor()
            columns = ", ".join(wordIndices_list[0].keys())
            placeholders = ":" + ", :".join(wordIndices_list[0].keys())
            sql = f"INSERT INTO WordIndices ({columns}) VALUES ({placeholders})"

            cursor.executemany(sql, wordIndices_list)
            self.words_db_connection.commit()
        return len(wordIndices_list)
