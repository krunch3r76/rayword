# wordsdbconnection.py
# Handles the connection setup and table creation for the 'words' database.

import sqlite3

# import schema version from constants TODO


def create_words_db_connection(db_path):
    conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
    create_tables(conn)
    return conn


def create_tables(conn):
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
    current_version = "1"
    description = "Initial schema version"

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version FROM schema_version ORDER BY applied_on DESC LIMIT 1"
        )
        result = cursor.fetchone()

        if result is None:
            # No version exists, insert the new version
            cursor.execute(
                "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                (current_version, description),
            )
        elif result[0] != current_version:
            # A different version exists, raise an exception
            raise Exception(
                f"Database schema version mismatch. Expected: {current_version}, Found: {result[0]}"
            )

        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"An error occurred: {e}")
        raise
