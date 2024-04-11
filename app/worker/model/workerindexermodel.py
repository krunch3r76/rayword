# app/worker/model/workerindexermodel.py
"""
    WorkerIndexerModel Module

    This module defines WorkerIndexerModel class for the rayword application.
    It provides CRUD (Create, Read, Update, Delete) interface for managing
    words, paths, and search histories in an in memory SQLite database.
"""
# provide an interface for the worker controller to query/update db

import sqlite3
import logging
import json
import bz2

from typing import Union
from .workerdbconnection import create_worker_db_connection

IP_TO_GUTENBERG_TEXTS = "69.55.231.8"


class WorkerIndexerModel:
    """
    A model for indexing and storing word and path data for a worker node in a database.

    This class provides methods to insert and retrieve word and path data from the database,
    as well as to export word indices as JSON.

    Attributes:
        path_prefix (str): The base URL prefix for paths.
        worker_db_connection (sqlite3.Connection): Connection to the worker's database.

    """

    def __init__(
        self,
        paths_table_dict,
        path_prefix=IP_TO_GUTENBERG_TEXTS,
    ):
        """
        Args:
            words_table_dict (dict): Dictionary containing word records to be inserted into the Words table.
            paths_table_dict (dict): Dictionary containing path records to be inserted into the Paths table.
            path_prefix (str, optional): Base URL prefix for paths. Defaults to "http://aleph.gutenberg.org".
        """

        # Guarantee a path_prefix
        if path_prefix is None:
            self.path_prefix = IP_TO_GUTENBERG_TEXTS
        else:
            self.path_prefix = path_prefix

        # Create the connecton
        self.worker_db_connection = create_worker_db_connection(in_memory=True)

        # Insert records
        self.start_transaction()
        self.insert_records_into_worker_db(paths_table_dict, "Paths")
        self.end_transaction()

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
                model.worker_db_connection.row_factory if use_row_factory else None
            )

        def __enter__(self):
            if self.use_row_factory:
                self.model.worker_db_connection.row_factory = sqlite3.Row
            self.cursor = self.model.worker_db_connection.cursor()
            return self.cursor

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.use_row_factory and self.original_row_factory is not None:
                self.model.worker_db_connection.row_factory = self.original_row_factory
            self.cursor.close()
            # Handle exceptions if necessary
            if exc_type:
                # Log or handle the exception
                pass

    def start_transaction(self):
        with self.cursor_context() as cursor:
            cursor.execute("BEGIN")

    def end_transaction(self):
        with self.cursor_context() as cursor:
            cursor.execute("COMMIT")

    def insert_word(self, word):
        """
        Inserts a word into the Words table if it doesn't exist and returns the word_id.

        Args:
            word (str): The word to be inserted.

        Returns:
            int: The word_id of the inserted or existing word.
        """
        word_id = self.get_word_id(word)
        if word_id is not None:
            return word_id

        with self.cursor_context() as cursor:
            cursor.execute("INSERT INTO Words (word) VALUES (?)", (word,))
            return cursor.lastrowid

    def insert_word_position(self, word_id, path_id, position):
        """
        Inserts a word position into the Positions table.

        Args:
            word_id (int): The word_id of the word.
            path_id (int): The path_id where the word is found.
            position (int): The position of the word in the text.
        """
        with self.cursor_context() as cursor:
            cursor.execute(
                "INSERT INTO Positions (word_id, path_id, position) VALUES (?, ?, ?)",
                (word_id, path_id, position),
            )

    def serialize_to_dict_or_compressed_json(
        self, compress: bool = False
    ) -> Union[dict, bytes]:
        """
        Serializes the database content to a dictionary mapping or compressed JSON.

        Args:
            compress (bool, optional): If True, serialize to compressed JSON. Defaults to False.

        Returns:
            Union[dict, bytes]: The serialized data as a dictionary or compressed JSON bytes.
        """
        # Fetch the word data from the database
        word_data = self.fetch_word_data()

        if compress:
            # Convert to JSON and then compress
            json_data = json.dumps(word_data)
            compressed_data = bz2.compress(json_data.encode("utf-8"))
            return compressed_data
        else:
            return word_data

    def _fetch_word_data(self) -> dict:
        """
        Fetches words and their positions from the database, organized by path.

        Returns:
            dict: A dictionary mapping paths to another dictionary, which maps words to their positions.
        """
        path_word_positions = {}
        query = """
            SELECT pa.path, w.word, p.position
            FROM Words w
            INNER JOIN Positions p ON w.word_id = p.word_id
            INNER JOIN Paths pa ON p.path_id = pa.path_id
            ORDER BY pa.path, w.word, p.position
        """

        with self.cursor_context(use_row_factory=True) as cursor:
            cursor.execute(query)
            for row in cursor:
                path = row["path"]
                word = row["word"]
                position = row["position"]

                if path not in path_word_positions:
                    path_word_positions[path] = {}

                if word not in path_word_positions[path]:
                    path_word_positions[path][word] = []

                path_word_positions[path][word].append(position)

        return path_word_positions

    def fetch_word_data(self) -> dict:
        """
        Fetches words and their positions from the database, organized by path.
        Processes and deletes the data in batches.

        Returns:
            dict: A dictionary mapping paths to another dictionary, which maps words to their positions.
        """
        BATCH_SIZE = 999
        path_word_positions = {}
        total_word_ids = set()

        # Function to process a batch of words and delete them
        def process_batch(batch_word_ids):
            self.delete_word_positions_by_ids(batch_word_ids)
            with self.cursor_context() as cursor:
                cursor.execute("VACUUM")

        # Function to fetch a batch of data
        def fetch_batch(last_word_id=None):
            batch_word_ids = set()
            query = """
                SELECT pa.path, w.word_id, w.word, p.position
                FROM Words w
                INNER JOIN Positions p ON w.word_id = p.word_id
                INNER JOIN Paths pa ON p.path_id = pa.path_id
                {}
                ORDER BY pa.path, w.word, p.position
                LIMIT {}
            """.format(
                f"WHERE w.word_id > {last_word_id}" if last_word_id else "", BATCH_SIZE
            )

            with self.cursor_context(use_row_factory=True) as cursor:
                cursor.execute(query)
                for row in cursor:
                    path = row["path"]
                    word_id = row["word_id"]
                    word = row["word"]
                    position = row["position"]

                    if path not in path_word_positions:
                        path_word_positions[path] = {}
                    if word not in path_word_positions[path]:
                        path_word_positions[path][word] = []

                    path_word_positions[path][word].append(position)
                    batch_word_ids.add(word_id)

            return batch_word_ids

        # Main loop for fetching and processing data
        last_processed_word_id = None
        while True:
            batch_word_ids = fetch_batch(last_processed_word_id)
            if not batch_word_ids:
                break  # Exit loop if no more data to fetch
            last_processed_word_id = max(batch_word_ids)
            total_word_ids.update(batch_word_ids)

            # Process the batch
            process_batch(batch_word_ids)

        return path_word_positions

    def delete_and_vacuum(self, word_ids):
        """
        Deletes position records for a set of word_ids and then vacuums the database.

        Args:
            word_ids (set): The set of word_ids for which to delete position records.
        """
        self.delete_word_positions_by_ids(word_ids)

        # Vacuum the database
        with self.cursor_context() as cursor:
            cursor.execute("VACUUM")

    def delete_word_positions_by_ids(self, word_ids):
        """
        Deletes position records for a set of word_ids.

        Args:
            word_ids (set): The set of word_ids for which to delete position records.
        """
        word_ids_list = list(word_ids)
        MAX_VARIABLES = (
            999  # SQLite limit for the number of host parameters in a statement
        )
        for i in range(0, len(word_ids_list), MAX_VARIABLES):
            chunk = word_ids_list[i : i + MAX_VARIABLES]
            word_ids_tuple = tuple(chunk)

            with self.cursor_context() as cursor:
                query = "DELETE FROM Positions WHERE word_id IN ({})".format(
                    ",".join("?" * len(word_ids_tuple))
                )
                cursor.execute(query, word_ids_tuple)

    def __fetch_word_data(self) -> dict:
        """
        Fetches words and their positions from the database, organized by path,
        and deletes the position records for each word after fetching.

        Returns:
            dict: A dictionary mapping paths to another dictionary, which maps words to their positions.
        """
        path_word_positions = {}
        fetched_word_ids = set()

        query = """
            SELECT pa.path, w.word_id, w.word, p.position
            FROM Words w
            INNER JOIN Positions p ON w.word_id = p.word_id
            INNER JOIN Paths pa ON p.path_id = pa.path_id
            ORDER BY pa.path, w.word, p.position
        """

        with self.cursor_context(use_row_factory=True) as cursor:
            cursor.execute(query)
            for row in cursor:
                path = row["path"]
                word_id = row["word_id"]
                word = row["word"]
                position = row["position"]

                if path not in path_word_positions:
                    path_word_positions[path] = {}
                if word not in path_word_positions[path]:
                    path_word_positions[path][word] = []

                path_word_positions[path][word].append(position)
                fetched_word_ids.add(word_id)

        # Delete position records for the fetched words
        self.delete_word_positions_by_ids(fetched_word_ids)

        return path_word_positions

    def __delete_word_positions_by_ids(self, word_ids):
        """
        Deletes position records for a set of word_ids by splitting the set into
        smaller chunks if necessary.

        Args:
            word_ids (set): The set of word_ids for which to delete position records.
        """
        MAX_VARIABLES = (
            999  # SQLite limit for the number of host parameters in a statement
        )
        word_ids_list = list(word_ids)

        # Split word_ids into smaller chunks
        for i in range(0, len(word_ids_list), MAX_VARIABLES):
            chunk = word_ids_list[i : i + MAX_VARIABLES]
            word_ids_tuple = tuple(chunk)

            with self.cursor_context() as cursor:
                query = "DELETE FROM Positions WHERE word_id IN ({})".format(
                    ",".join("?" * len(word_ids_tuple))
                )
                cursor.execute(query, word_ids_tuple)

    def get_word_id(self, word):
        """
        Retrieves the word_id for a given word from the database.

        Args:
            word (str): The word for which to find the word_id.

        Returns:
            int: The word_id of the given word or None if not found.
        """
        with self.cursor_context(use_row_factory=True) as cursor:
            cursor.execute("SELECT word_id FROM Words WHERE word = ?", (word,))
            result = cursor.fetchone()
            return result["word_id"] if result else None

    def cursor_context(self, use_row_factory=False):
        return WorkerIndexerModel.CursorContextManager(self, use_row_factory)

    def insert_records_into_worker_db(self, records_list, table_name):
        """
        Inserts a list of records into the specified table in the worker database.

        This method dynamically constructs and executes an SQL INSERT query based on the field names
        and values in the records_list.

        Args:
            records_list (list of dict): A list of dictionaries, each representing a record to be inserted.
                                         Each dictionary should have keys corresponding to the table's column names.
            table_name (str): The name of the table where records will be inserted.
        """
        # Check if records_list is empty
        if not records_list:
            return

        # Extract field names sampling the first record
        field_names = records_list[0].keys()
        field_placeholders = ", ".join(["?" for _ in field_names])
        field_names_str = ", ".join(field_names)

        with self.cursor_context() as cursor:
            # SQL query to insert data dynamically based on field names
            query = f"INSERT INTO {table_name} ({field_names_str}) VALUES ({field_placeholders})"

            # Insert each record into the table
            for record in records_list:
                cursor.execute(query, tuple(record[field] for field in field_names))

    def select_path_records(self, fields=None, order_by_path_id=True):
        """
        Retrieves a list of Path records from the database

        Args:
            fields (list, optional): A list of field names to be included in the result.
            order_by_path_id (bool, optional): Whether to order the results by path_id. Defaults to True.

        Returns:
            list of tuple: A list of tuples, each containing the selected fields from the Paths table or empty list for no records.

        Notes:
            fields defaults to "path", "path_id" excluding text_number (not used by worker)
        """
        if fields is None:
            fields = ["path", "path_id"]

        # Join the fields list into a string for the SQL query
        fields_str = ", ".join(fields)

        with self.cursor_context() as cursor:
            query = f"SELECT {fields_str} FROM Paths"

            # Append 'ORDER BY path_id' if required
            if order_by_path_id:
                query += " ORDER BY path_id"

            cursor.execute(query)
            results = cursor.fetchall()

            if results:
                # Prepend path_prefix if 'path' is in the fields
                if "path" in fields:
                    path_index = fields.index("path")
                    results = [
                        (self.path_prefix + row[path_index],) + row[1:]
                        for row in results
                    ]

            return results

    def select_records(self, tablename, fields=None, use_row_factory=True):
        """
        Returns the records of the table.

        This method retrieves all records from the table and converts them
        into a list of dictionaries.

        Args:
            tablename (str): The name of the table from which to select records.
            fields (list, optional): A list of field names to be included in the result.

        Returns:
            list: A list of dictionaries of table records.

        Raises:
            TypeError: If 'fields' is not a list or None.
        """
        if fields is None:
            fields = ["*"]
        elif not isinstance(fields, (list, tuple)):
            raise TypeError("fields parameter must be a list or tuple of field names")

        fields_str = ", ".join(fields)

        with self.cursor_context(use_row_factory=use_row_factory) as cursor:
            cursor.execute(f"SELECT {fields_str} FROM {tablename}")
            records = cursor.fetchall()

        if use_row_factory:
            return [dict(record) for record in records]
        else:
            return records
