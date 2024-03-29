# contextdbconnection.py
# Manages the database connection and initial setup for the 'textdetails' database.
import sqlite3


def create_text_details_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    create_tables(conn)
    return conn


def create_tables(conn):
    # SQL statements to create tables in the context database
    # conn.execute(
    #     """CREATE TABLE IF NOT EXISTS Context (
    #                     word_indices_id INTEGER PRIMARY KEY,
    #                     sentence TEXT,
    #                     paragraph TEXT,
    #                     text_number INTEGER
    #                 );"""
    # )
    # Additional table creation as needed
    ddls = [
        """CREATE TABLE IF NOT EXISTS Meta (
    TextNumber INT,
    Type TEXT,
    Issued TEXT,
    Title TEXT,
    Language TEXT,
    Authors TEXT,
    Subjects TEXT,
    LoCC TEXT,
    Bookshelves TEXT
)""",
    ]
    conn.commit()

    for ddl_statement in ddls:
        try:
            conn.execute(ddl_statement)
        except sqlite3.OperationalError as e:
            print(f"exception thrown when executing:\n\t{ddl_statement}\n")
            print(e)
            raise
    conn.commit()
