# contextdbconnection.py
# Manages the database connection and initial setup for the 'context' database.
# deprecated
import sqlite3


def create_context_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    return conn


def create_tables(conn):
    # SQL statements to create tables in the context database
    conn.execute(
        """CREATE TABLE IF NOT EXISTS Context (
                        word_indices_id INTEGER PRIMARY KEY,
                        sentence TEXT,
                        paragraph TEXT,
                        text_number INTEGER
                    );"""
    )
    # Additional table creation as needed
    conn.commit()
