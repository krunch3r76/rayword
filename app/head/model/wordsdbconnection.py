# wordsdbconnection.py
# Handles the connection setup and table creation for the 'words' database.

import sqlite3
import os

# import schema version from constants TODO


def remove_db_file(conn, db_file_path):
    # Close the connection before attempting to remove the file
    conn.close()

    # Remove the file
    os.remove(db_file_path)
    print(f"Removed file: {db_file_path}")


def create_words_db_connection(db_path, model):
    SUCCESSFUL = False
    while not SUCCESSFUL:
        # conn = sqlite3.connect(":memory:", isolation_level=None)
        conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
        model.words_db_connection = conn
        SUCCESSFUL = create_tables(conn, db_path, model)
    return conn


# def save_db_to_file(conn, filename):
#     # Connect to a database file
#     with sqlite3.connect(filename) as disk_conn:
#         # Copy the data from the in-memory database to the disk database
#         for line in conn.iterdump():
#             if "CREATE TABLE" in line:
#                 disk_conn.execute(line)
#             elif "INSERT INTO" in line:
#                 disk_conn.execute(line)

#     # Commit changes and close the disk connection
#     disk_conn.commit()


def create_tables(conn, db_path, model):
    # SQL statements to create tables in the words database
    # to do, allow for multiple paths given a text number
    ddls = [
        """CREATE TABLE IF NOT EXISTS Paths (
            path_id INTEGER PRIMARY KEY,
            path TEXT UNIQUE NOT NULL,
            text_number INTEGER NOT NULL,
            is_unreachable INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS WordIndices (
            word_indices_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            word_index INTEGER NOT NULL,
            text_number INTEGER NOT NULL,
            UNIQUE (word, word_index, text_number)
        )""",
        """CREATE TABLE IF NOT EXISTS SearchHistory (
            search_id INTEGER PRIMARY KEY AUTOINCREMENT,
            text_number INTEGER NOT NULL,
            FOREIGN KEY (text_number) REFERENCES Paths(text_number),
            UNIQUE (text_number)
        )""",
        """CREATE TABLE IF NOT EXISTS schema_version (
            version VARCHAR(50) PRIMARY KEY,
            applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )""",
    ]
    # ddls = [
    #     """CREATE TABLE IF NOT EXISTS Words (
    #         word_id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         word TEXT UNIQUE,
    #     )""",
    #     """CREATE TABLE IF NOT EXISTS Paths (
    #         path_id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         path TEXT UNIQUE,
    #         text_number INTEGER UNIQUE,
    #         is_unreachable INTEGER DEFAULT 0
    #     )""",
    #     """CREATE TABLE IF NOT EXISTS WordIndices (
    #         word_indices_id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         word_id INTEGER,
    #         word_index INTEGER,
    #         FOREIGN KEY (word_id) REFERENCES Words(word_id),
    #         FOREIGN KEY (path_id) REFERENCES Paths(path_id),
    #         UNIQUE (word_id, word_index, path_id)
    #     )""",
    #     """CREATE TABLE IF NOT EXISTS SearchHistory (
    #         search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         text_number INTEGER,
    #         FOREIGN KEY (word_id) REFERENCES Words(word_id),
    #         FOREIGN KEY (path_id) REFERENCES Paths(path_id),
    #         UNIQUE (path_id)
    #     )""",
    #     """CREATE TABLE IF NOT EXISTS schema_version (
    #         version VARCHAR(50) PRIMARY KEY,
    #         applied_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         description TEXT
    #     )""",
    # ]

    for ddl_statement in ddls:
        try:
            conn.execute(ddl_statement)

        except sqlite3.OperationalError as e:
            print(f"exception thrown when executing:\n{ddl_statement}\n")
            print(e)
            raise

    # Additional table creation as needed
    conn.commit()

    # Check for an existing version
    current_version = "4"
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
            if internal_version != current_version:
                remove_db_file(conn, db_path)
                return False

        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"An error occurred: {e}")
        raise

    return True
