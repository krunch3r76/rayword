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
import bz2

from .wordsdbconnection import create_words_db_connection
from constants import WORDS_DB_FILE, TEXT_DETAILS_DB_FILE

from .contextdbconnection import create_text_details_db_connection

logger = logging.getLogger()


class WordIndexerModel:
    """
    A persistent model for indexing and storing paths and word search histories.

    Provides serialization methods for sharing relevant data to remote nodes.

    Attributes:
        words_db_connection (sqlite3.connection):
    """

    def __init__(
        self,
        path_records_to_insert,
    ):
        """
        Args:
            path_records_to_insert (list of dicts): records corresponding to Path table entries to insert
        """
        if WORDS_DB_FILE.exists():
            WORDS_DB_FILE.unlink(missing_ok=True)

        self.words_db_connection = create_words_db_connection(WORDS_DB_FILE, self)
        self.insert_path_records(path_records_to_insert)

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

    def cursor_context(self, use_row_factory=False):
        return WordIndexerModel.CursorContextManager(
            model=self, use_row_factory=use_row_factory
        )

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

    def get_unreachable_paths(self):
        """Select path values from Paths for which is_unreachable = 1 and return as a list"""
        unreachable_paths = []
        query = "SELECT path FROM Paths WHERE is_unreachable = 1"
        with self.cursor_context(use_row_factory=True) as cursor:
            cursor.execute(query)
            unreachable_paths = [row["path"] for row in cursor.fetchall()]
        return unreachable_paths

    def get_text_numbers_searched(self):
        """Select text_number values from SearchHistory"""
        text_numbers_searched = []
        query = "SELECT text_number from SearchHistory"
        with self.cursor_context() as cursor:
            cursor.execute(query)
            text_numbers_searched = [row[0] for row in cursor.fetchall()]
        return text_numbers_searched

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

    def _fetch_table_data(self, table_name):
        """Fetch data from the specified table and return it as a list of dictionaries."""
        with self.cursor_context(use_row_factory=True) as cursor:
            cursor.execute(f"SELECT * FROM {table_name}")
            return [dict(row) for row in cursor.fetchall()]

    def export_table_to_file(self, table_name, filepath, compress=False):
        """Export specified table to the specified path, with optional bzip2 compression."""
        data = self._fetch_table_data(table_name)
        serialized_data = json.dumps(data).encode("utf-8")

        if compress:
            compressed_data = bz2.compress(serialized_data)
            with open(filepath, "wb") as file:
                file.write(compressed_data)
        else:
            with open(filepath, "wb") as file:
                file.write(serialized_data)

    def _cursor(self):
        """
        Creates and returns a new cursor object from the database connection.

        Returns:
            sqlite3.Cursor: A new cursor object for the database.
        """
        return self.words_db_connection.cursor()

    def get_path_records(self):
        """
        Retrieves a list of all path_ids from the Paths table.

        Returns:
            list of int: a list of path_ids
        """
        with self.cursor_context(use_row_factory=True) as cursor:
            cursor.execute("SELECT * FROM Paths")
            return [dict(row) for row in cursor.fetchall()]
            # return [row["path"] for row in cursor.fetchall()]

    def insert_search_histories(self, path_ids_searched):
        """
        Find the text_number corresponding to each path_id in the Paths table and insert a new
        SearchHistory record with this text_number.

        Args:
            path_ids_searched (list): List of path_ids to be searched in the Paths table.
        """
        # Retrieve text_numbers corresponding to the provided path_ids
        text_numbers = []
        with self.cursor_context(use_row_factory=True) as cursor:
            for path_id in path_ids_searched:
                cursor.execute(
                    "SELECT text_number FROM Paths WHERE path_id = ?", (path_id,)
                )
                result = cursor.fetchone()
                if result:
                    text_numbers.append(result["text_number"])

        # Insert new records into SearchHistory
        with self.cursor_context() as cursor:
            insert_query = "INSERT INTO SearchHistory (text_number) VALUES (?)"
            cursor.executemany(
                insert_query, [(text_number,) for text_number in text_numbers]
            )
            self.words_db_connection.commit()

    def insert_path_records(self, path_records_list):
        """update model with path records"""
        if len(path_records_list) > 0:
            cursor = self._cursor()
            columns = ", ".join(path_records_list[0].keys())
            placeholders = ":" + ", :".join(path_records_list[0].keys())
            sql = f"INSERT INTO Paths ({columns}) VALUES ({placeholders})"

            cursor.executemany(sql, path_records_list)
            self.words_db_connection.commit()

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

    def lookup_text_number_by_path_id(self, path_id):
        """
        Retrieves the text_number associated with a given path_id.

        Args:
            path_id (int): The path_id for which to find the corresponding text_number.

        Returns:
            int: The text_number associated with the given path_id, or None if not found.
        """
        with self.cursor_context(use_row_factory=True) as cursor:
            cursor.execute(
                "SELECT text_number FROM Paths WHERE path_id = ?", (path_id,)
            )
            result = cursor.fetchone()
            return result["text_number"] if result else None
