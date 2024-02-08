# workerdbconnection.py
# create connection and initialize database if needed

import sqlite3


def create_tables(conn):
    # SQL statements to create tables in the words database
    ddls = [
        """CREATE TABLE IF NOT EXISTS Paths (
            path_id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            text_number INTEGER UNIQUE,
            is_unreachable INTEGER -- not used here
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
