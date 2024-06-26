import argparse
import csv
import os
from dotenv import load_dotenv

import psycopg2

load_dotenv()  # take environment variables from .env.

conn_url = os.getenv("DATABASE_URL")
print(conn_url)


def create_connection():
    """create a database connection to a PostgreSQL database"""
    conn = None
    try:
        conn = psycopg2.connect(conn_url)
        cursor = conn.cursor()
        # Execute a sample query
        cursor.execute("SELECT version();")

        # Fetch and print the result
        db_version = cursor.fetchone()
        print("PostgreSQL database version:", db_version)
    except psycopg2.Error as e:
        print(e)
    return conn


def create_table(conn, create_table_sql):
    """create a table from the create_table_sql statement"""
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except psycopg2.Error as e:
        print(e)


def search_in_column(table_name: str, column_name: str, query: str):
    conn = create_connection()
    cursor = conn.cursor()
    if column_name.endswith("id"):
        sql_query = f"SELECT * FROM {table_name} WHERE {column_name} = %s"
        cursor.execute(sql_query, (query,))
    else:
        sql_query = f"SELECT * FROM {table_name} WHERE {column_name} LIKE %s"
        cursor.execute(sql_query, ("%" + query + "%",))

    matching_rows = cursor.fetchall()

    response = []
    for row in matching_rows:
        response.append(row)

    conn.close()
    return response


# ================================ PELIGROSO ===========================
def drop_table(table_name):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    conn.commit()
    print(f"Table {table_name} is dead")
    conn.close()


def drop_all_tables():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
    )
    tables = cursor.fetchall()

    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")

    conn.commit()
    print(f"All Tables are dead")
    conn.close()


def force_drop_all_tables():
    try:
        conn = create_connection()
        cursor = conn.cursor()

        # Get all table names in the current schema
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';"
        )

        table_names = cursor.fetchall()

        # Drop each table with CASCADE option to drop dependencies
        for table_name in table_names:
            cursor.execute(f"DROP TABLE IF EXISTS {table_name[0]} CASCADE;")
            print(f"Force dropped table: {table_name[0]}")

        conn.commit()
        cursor.close()
        conn.close()
        print("All tables force dropped successfully!")

    except psycopg2.Error as e:
        conn.rollback()
        print("Error force dropping tables:", e)


def create_tables():
    sql_create_users_table = """ CREATE TABLE IF NOT EXISTS users (
                                        user_id TEXT PRIMARY KEY,
                                        email TEXT NOT NULL UNIQUE,
                                        password TEXT NOT NULL,
                                        created_at TIMESTAMP NOT NULL,
                                        last_login TIMESTAMP
                                    ); """

    sql_create_accounts_table = """CREATE TABLE IF NOT EXISTS accounts (
                                      account_id TEXT PRIMARY KEY,
                                      user_id TEXT NOT NULL,
                                      account_type TEXT NOT NULL,
                                      account_name TEXT NOT NULL,
                                      balance REAL NOT NULL,
                                      created_at TIMESTAMP NOT NULL,
                                      last_updated TIMESTAMP,
                                      FOREIGN KEY (user_id) REFERENCES users (user_id)
                                   );"""

    sql_create_categories_table = """CREATE TABLE IF NOT EXISTS categories (
                                        category_id TEXT PRIMARY KEY,
                                        category_name TEXT NOT NULL,
                                        category_type TEXT NOT NULL,
                                        custom BOOLEAN NOT NULL,
                                        user_id TEXT
                                     );"""

    sql_create_transactions_table = """CREATE TABLE IF NOT EXISTS transactions (
                                          transaction_id TEXT PRIMARY KEY,
                                          account_id TEXT NOT NULL,
                                          user_id TEXT NOT NULL,
                                          transaction_type TEXT NOT NULL,
                                          amount REAL NOT NULL,
                                          category_id TEXT NOT NULL,
                                          transaction_date DATE NOT NULL,
                                          description TEXT,
                                          created_at TIMESTAMP NOT NULL,
                                          FOREIGN KEY (account_id) REFERENCES accounts (account_id),
                                          FOREIGN KEY (user_id) REFERENCES users (user_id),
                                          FOREIGN KEY (category_id) REFERENCES categories (category_id)
                                       );"""

    sql_create_budgets_table = """CREATE TABLE IF NOT EXISTS budgets (
                                     budget_id TEXT PRIMARY KEY,
                                     user_id TEXT NOT NULL,
                                     category_id TEXT NOT NULL,
                                     amount REAL NOT NULL,
                                     start_date DATE NOT NULL,
                                     end_date DATE NOT NULL,
                                     FOREIGN KEY (category_id) REFERENCES categories (category_id)
                                  );"""

    sql_create_savings_goals_table = """CREATE TABLE IF NOT EXISTS savings_goals (
                                           goal_id TEXT PRIMARY KEY,
                                           user_id TEXT NOT NULL,
                                           goal_name TEXT NOT NULL,
                                           target_amount REAL NOT NULL,
                                           current_amount REAL NOT NULL DEFAULT 0,
                                           target_date DATE,
                                           created_at TIMESTAMP NOT NULL,
                                           FOREIGN KEY (user_id) REFERENCES users (user_id)
                                        );"""

    # create a database connection
    conn = create_connection()

    # create tables
    if conn is not None:
        create_table(conn, sql_create_users_table)
        print("users table created")
        create_table(conn, sql_create_accounts_table)
        print("accounts table created")
        create_table(conn, sql_create_categories_table)
        print("categories table created")
        create_table(conn, sql_create_transactions_table)
        print("transactions table created")
        create_table(conn, sql_create_budgets_table)
        print("budgest table created")
        create_table(conn, sql_create_savings_goals_table)
        print("savings table created")
        conn.commit()
        conn.close()
    else:
        print("Error! cannot create the database connection.")


def populate_table_from_csv(conn, table_name, csv_file):
    with open(csv_file, "r") as file:
        csv_reader = csv.reader(file)
        columns = next(csv_reader)  # Assume header row is present
        cursor = conn.cursor()
        for row in csv_reader:
            placeholders = ", ".join(["%s"] * len(row))
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
            cursor.execute(sql, row)
        conn.commit()


def populate_tables():
    conn = create_connection()

    tables = [
        "users",
        "accounts",
        "categories",
        "transactions",
        "budgets",
        "savings_goals",
    ]
    for table in tables:
        csv_file = f"data/mock_{table}_data.csv"
        print(f"table being populated: {table}")
        populate_table_from_csv(conn, table, csv_file)

    print("Finished Populating")
    conn.close()


#  Methods used by the services
def get_all_table_data(table_name):
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table_name}")
    records = cursor.fetchall()

    conn.close()

    return records


# Update a row in a table by its id and id_type
def update_row_by_id(table_name, id_type, row_id, updated_details):
    conn = create_connection()
    cursor = conn.cursor()

    # Build the SQL query dynamically based on the fields provided in updated_details
    set_clause = ", ".join([f"{key} = %s" for key in updated_details.keys()])
    sql_query = f"UPDATE {table_name} SET {set_clause} WHERE {id_type} = %s"

    # Prepare the values for the placeholders in the SQL query
    values = list(updated_details.values())
    values.append(row_id)  # Add order_id to the end of values list for the WHERE clause

    cursor.execute(sql_query, values)
    conn.commit()
    conn.close()


def delete_row_by_id(table_name, id_type, row_id):
    conn = create_connection()
    cursor = conn.cursor()

    sql_query = f"DELETE FROM {table_name} WHERE {id_type} = %s"

    cursor.execute(sql_query, (row_id,))

    conn.commit()
    conn.close()


def get_user_all_table_data(table_name, user_id):
    conn = create_connection()
    cursor = conn.cursor()

    if table_name == "categories":
        query = f"SELECT * FROM {table_name} WHERE user_id = ? OR custom = FALSE", (
            user_id,
        )
    else:
        query = f"SELECT * FROM {table_name} WHERE user_id = %s", (user_id,)
    cursor.execute(*query)
    records = cursor.fetchall()

    conn.close()
    return records


def main(args):
    if args.drop:
        drop_all_tables()
    if args.fdrop:
        force_drop_all_tables()
    if args.create:
        create_tables()
    if args.populate:
        populate_tables()


# usage: python database.py --drop --create --populate
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage database.")
    parser.add_argument("--drop", action="store_true", help="Drop all tables.")
    parser.add_argument("--fdrop", action="store_true", help="Force drop all tables.")
    parser.add_argument("--create", action="store_true", help="Create all tables.")
    parser.add_argument("--populate", action="store_true", help="Populate all tables.")
    args = parser.parse_args()

    main(args)
