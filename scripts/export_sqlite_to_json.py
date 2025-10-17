#!/usr/bin/env python3
"""
Export data from SQLite database to JSON files.
"""

import argparse
import json
import logging
import os
import sqlite3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def export_table_to_json(db_path: str, table_name: str, output_dir: str):
    """Export a table from SQLite to a JSON file."""

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        logger.info(f"Exporting table '{table_name}' from {db_path}...")

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        if not rows:
            logger.info(f"Table '{table_name}' is empty. Nothing to export.")
            return

        data = [dict(row) for row in rows]

        output_path = os.path.join(output_dir, f"{table_name}.json")
        with open(output_path, "w") as f:
            json.dump(data, f, indent=4)

        logger.info(f"✅ Successfully exported {len(data)} rows from '{table_name}' to {output_path}")

    except sqlite3.Error as e:
        logger.error(f"Error exporting table '{table_name}': {e}")
    finally:
        if conn:
            conn.close()


def main():
    """Main function"""

    parser = argparse.ArgumentParser(description="Export SQLite data to JSON.")
    parser.add_argument("db_path", help="Path to the SQLite database file.")
    args = parser.parse_args()

    if not os.path.exists(args.db_path):
        logger.error(f"Database file not found: {args.db_path}")
        return

    output_dir = "data/json"
    os.makedirs(output_dir, exist_ok=True)

    # Get all tables from the database
    try:
        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error connecting to database or fetching tables: {e}")
        return
    finally:
        if conn:
            conn.close()

    logger.info(f"Found tables in {args.db_path}: {tables}")

    # Tables to ignore
    ignored_tables = [
        'products_fts',
        'products_fts_data',
        'products_fts_idx',
        'products_fts_docsize',
        'products_fts_config',
        'sqlite_sequence',
        'sqlite_stat1',
        'sqlite_stat4'
    ]

    for table in tables:
        if table in ignored_tables:
            logger.info(f"Ignoring table: {table}")
            continue
        export_table_to_json(args.db_path, table, output_dir)


if __name__ == "__main__":
    main()
