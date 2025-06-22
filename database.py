import sqlite3
import json
import logging

# Set up a logger for the database module
logger = logging.getLogger(__name__)

DATABASE_FILE = "data/flatool.db"


def init():
    """
    Initializes the SQLite database and creates the 'config' table if it doesn't exist.
    The 'config' table will store key-value pairs for our bot configuration.
    """
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS counting (
            channel_id INTEGER PRIMARY KEY,
            value INTEGER
            )
        """
        )
        conn.commit()
        conn.close()
        logger.info(f"Database '{DATABASE_FILE}' initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)


def save_config(config_data: dict):
    """
    Saves the current configuration dictionary to the database.
    Each item in the dictionary is stored as a key-value pair.
    Values are converted to JSON strings for storage to handle lists/None.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        for key, value in config_data.items():
            # Convert values (especially lists like roles_to_track or None) to JSON strings
            json_value = json.dumps(value)
            cursor.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, json_value),
            )
        conn.commit()
        logger.info("Configuration saved to database.")
    except sqlite3.Error as e:
        logger.error(f"Error saving configuration to database: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def load_config() -> dict:
    """
    Loads the configuration dictionary from the database.
    Values are read as JSON strings and converted back to Python objects.
    Provides default values if no configuration is found in the database.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM config")
        rows = cursor.fetchall()

        loaded_config = {}
        for key, value_json in rows:
            # Convert JSON strings back to Python objects
            loaded_config[key] = json.loads(value_json)

        # Merge with default config to ensure all keys are present,
        # especially for new installations or missing keys.
        # Ensure default types match what's expected.
        default_config = {
            "role_embed_channel_id": None,
            "role_embed_message_id": None,
            "roles_to_track": [],
            "embed_title": "👥 Role Member Tracker",
        }
        # Update default_config with any values loaded from the DB
        # This preserves DB values while ensuring defaults for missing keys
        merged_config = {**default_config, **loaded_config}

        logger.info("Configuration loaded from database.")
        return merged_config

    except sqlite3.Error as e:
        logger.error(f"Error loading configuration from database: {e}", exc_info=True)
        # Return default config if there's a database error
        return {
            "role_embed_channel_id": None,
            "role_embed_message_id": None,
            "roles_to_track": [],
            "embed_title": "👥 Role Member Tracker",
        }
    finally:
        if conn:
            conn.close()


def clear_config():
    """
    Resets the configuration in the database to default values.
    Deletes all existing config entries and inserts defaults.
    """
    default_config = {
        "role_embed_channel_id": None,
        "role_embed_message_id": None,
        "roles_to_track": [None],
        "embed_title": "Role Member Tracker",
    }
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM config")
        for key, value in default_config.items():
            json_value = json.dumps(value)
            cursor.execute(
                "INSERT INTO config (key, value) VALUES (?, ?)",
                (key, json_value),
            )
        conn.commit()
        logger.info("Configuration reset to default values.")
    except sqlite3.Error as e:
        logger.error(f"Error resetting configuration: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def create_counting_row(channel_id: int, value: int):
    """
    Ensures only one row exists in the counting table.
    Deletes any existing rows, then inserts the new row.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        # Delete all existing rows to enforce only one row
        cursor.execute("DELETE FROM counting")
        # Insert the new row
        cursor.execute(
            "INSERT INTO counting (channel_id, value) VALUES (?, ?)",
            (channel_id, value),
        )
        conn.commit()
        logger.info(
            f"Counting table reset with channel_id={channel_id}, value={value}."
        )
    except sqlite3.Error as e:
        logger.error(f"Error setting counting row: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def get_counting_row():
    """
    Retrieves the single row from the counting table.
    Returns a tuple (channel_id, value) if present, else None.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id, value FROM counting LIMIT 1")
        row = cursor.fetchone()
        return row  # Returns (channel_id, value) or None
    except sqlite3.Error as e:
        logger.error(f"Error retrieving counting row: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()


def update_counting_value(new_value: int):
    """
    Updates the value in the counting table to the specified new_value.
    Assumes there is only one row in the table.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE counting SET value = ?", (new_value,))
        conn.commit()
        logger.info(f"Counting value updated to {new_value}.")
    except sqlite3.Error as e:
        logger.error(f"Error updating counting value: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


# Initialize the database when this module is imported
init()
