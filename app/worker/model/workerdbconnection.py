# workerdbconnection.py
# create connection and initialize database if needed

import sqlite3


def create_tables(conn):
    # SQL statements to create tables in the words database
    ddls = [
        """CREATE TABLE IF NOT EXISTS Words (
            word_id INTEGER PRIMARY KEY,
            word TEXT UNIQUE,
            form_group_id INTEGER
        )""",
        # """CREATE TABLE IF NOT EXISTS FormGroups (
        #     form_group_id INTEGER PRIMARY KEY
        # )""",
        """CREATE TABLE IF NOT EXISTS Paths (
            path_id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            text_number INTEGER UNIQUE,
            is_unreachable INTEGER -- not used here
        )""",
        # """CREATE TABLE IF NOT EXISTS Hashes (
        #     hash_id INTEGER PRIMARY KEY AUTOINCREMENT,
        #     path_id INTEGER,
        #     compressed_file_hash TEXT,
        #     decompressed_text_hash TEXT,
        #     FOREIGN KEY (path_id) REFERENCES Paths(path_id)
        # )""",
        """CREATE TABLE IF NOT EXISTS WordIndices (
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
            FOREIGN KEY (path_id) REFERENCES Paths(path_id)
        )""",
        """CREATE TABLE IF NOT EXISTS SearchHistory (
            word_id INTEGER,
            path_id INTEGER,
            FOREIGN KEY (word_id) REFERENCES Words(word_id),
            FOREIGN KEY (path_id) REFERENCES Paths(path_id)
        )""",
    ]

    for ddl_statement in ddls:
        try:
            conn.execute(ddl_statement)
        except sqlite3.OperationalError as e:
            print(f"exception thrown when executing:\n{ddl_statement}\n")
            print(e)


def create_worker_db_connection():
    # return an in memory database connection
    conn = sqlite3.connect(":memory:", isolation_level=None)
    create_tables(conn)
    return conn
