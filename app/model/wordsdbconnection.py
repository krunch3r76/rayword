# wordsdbconnection.py
# Handles the connection setup and table creation for the 'words' database.

import sqlite3
import os

# import schema version from constants TODO


# def check_schema_condition(conn):
#     # Replace this function with the actual check you need to perform.
#     # Return True if the schema condition is met, False otherwise.
#     # Example: Check if a specific table or column exists

#     cursor = conn.cursor()
#     cursor.execute(
#         "SELECT version FROM schema_version ORDER BY applied_on DESC LIMIT 1"
#     )


def remove_db_file(conn, db_file_path):
    # Close the connection before attempting to remove the file
    conn.close()

    # Remove the file
    os.remove(db_file_path)
    print(f"Removed file: {db_file_path}")


def create_words_db_connection(db_path, model):
    SUCCESSFUL = False
    while not SUCCESSFUL:
        conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
        model.words_db_connection = conn
        SUCCESSFUL = create_tables(conn, db_path, model)
    return conn


def create_tables(conn, db_path, model):
    # SQL statements to create tables in the words database
    # to do, allow for multiple paths given a text number
    ddls = [
        """CREATE TABLE IF NOT EXISTS Words (
            word_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            form_group_id INTEGER,
            FOREIGN KEY (form_group_id) REFERENCES FormGroups(form_group_id)
        )""",
        """CREATE TABLE IF NOT EXISTS FormGroups (
            form_group_id INTEGER PRIMARY KEY AUTOINCREMENT
        )""",
        """CREATE TABLE IF NOT EXISTS Paths (
            path_id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            text_number INTEGER UNIQUE,
            is_unreachable INTEGER DEFAULT 0
        )""",
        # """CREATE TABLE IF NOT EXISTS Hashes (
        #     hash_id INTEGER PRIMARY KEY AUTOINCREMENT,
        #     path_id INTEGER,
        #     compressed_file_hash TEXT,
        #     decompressed_text_hash TEXT,
        #     FOREIGN KEY (path_id) REFERENCES Paths(path_id)
        # )""",
        """CREATE TABLE IF NOT EXISTS WordIndices (
            word_indices_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER,
            word_index INTEGER,
            sentence_index_start INTEGER,
            sentence_index_end INTEGER,
            paragraph_index_start INTEGER,
            paragraph_index_end INTEGER,
            path_id INTEGER,
            context_sentence TEXT DEFAULT "",
            context_paragraph TEXT DEFAULT "",
            FOREIGN KEY (word_id) REFERENCES Words(word_id),
            FOREIGN KEY (path_id) REFERENCES Paths(path_id),
            UNIQUE (word_id, word_index, path_id)
        )""",
        """CREATE TABLE IF NOT EXISTS SearchHistory (
            search_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER,
            path_id INTEGER,
            FOREIGN KEY (word_id) REFERENCES Words(word_id),
            FOREIGN KEY (path_id) REFERENCES Paths(path_id),
            UNIQUE (word_id, path_id)
        )""",
        """CREATE TABLE IF NOT EXISTS schema_version (
            version VARCHAR(50) PRIMARY KEY,
            applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS History (
            id INTEGER PRIMARY KEY CHECK (id=1),
            ultimate_max_index_id INTEGER DEFAULT 0,
            penultimate_max_index_id INTEGER DEFAULT 0
            )
            """,
    ]

    for ddl_statement in ddls:
        try:
            conn.execute(ddl_statement)

        except sqlite3.OperationalError as e:
            print(f"exception thrown when executing:\n{ddl_statement}\n")
            print(e)

    # Additional table creation as needed
    conn.commit()

    # Check for an existing version
    current_version = "3"
    description = "Add History table"

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version FROM schema_version ORDER BY applied_on DESC LIMIT 1"
        )
        result = cursor.fetchone()
        internal_version = None
        if result is None:
            # No version exists, insert the new version
            cursor.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (current_version, description),
            )
        else:
            internal_version = result[0]
            if internal_version == "1" or internal_version == "2":
                remove_db_file(conn, db_path)
                return False

        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"An error occurred: {e}")
        raise

    return True
