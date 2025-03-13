# main/model/pathsdbconnection.py


import sqlite3
import os
import logging

# import schema version from constants TODO


def remove_db_file(conn, db_file_path):
    # Close the connection before attempting to remove the file
    conn.close()

    # Remove the file
    os.remove(db_file_path)
    print(f"Removed file: {db_file_path}")


def create_paths_db_connection(db_path):
    SUCCESSFUL = False
    while not SUCCESSFUL:
        # conn = sqlite3.connect(":memory:", isolation_level=None)
        conn = sqlite3.connect(db_path, isolation_level="IMMEDIATE")
        SUCCESSFUL = create_tables(conn, db_path)
    return conn


def create_tables(conn, db_path):
    # SQL statements to create tables in the words database
    # to do, allow for multiple paths given a text number
    ddls = [
        """CREATE TABLE IF NOT EXISTS Paths (
            path_id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            text_number INTEGER
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
            raise

    # Additional table creation as needed
    conn.commit()

    # Check for an existing version
    current_version = "2"
    description = "first"

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
            if internal_version != current_version:
                print("Discarding old paths database")
                remove_db_file(conn, db_path)
                return False

        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"An error occurred: {e}")
        raise

    return True
