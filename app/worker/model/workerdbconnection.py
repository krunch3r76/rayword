# workerdbconnection.py
# create connection and initialize database if needed

import sqlite3
import uuid


def create_tables(conn):
    ddls = [
        """CREATE TABLE IF NOT EXISTS Paths (
            path_id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            text_number INTEGER UNIQUE,
            is_unreachable INTEGER -- not used here
        )""",
        """CREATE TABLE IF NOT EXISTS Words (
            word_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE
        )""",
        """CREATE TABLE IF NOT EXISTS Positions (
            position_id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER,
            path_id INTEGER,
            position INTEGER,
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


def create_worker_db_connection(in_memory=True):
    """
    Returns a database connection.
    For in-memory databases, it creates a new database each time.
    For on-disk databases, it creates a uniquely named database file.

    Args:
        in_memory (bool, optional): Whether to create an in-memory database. Defaults to True.

    Returns:
        sqlite3.Connection: The database connection.
    """
    if in_memory:
        conn = sqlite3.connect(":memory:", isolation_level=None)
    else:
        # Generate a unique filename using uuid4
        db_filename = f"/tmp/worker_indexer_{uuid.uuid4()}.db"
        conn = sqlite3.connect(db_filename, isolation_level=None)

    create_tables(conn)
    return conn
