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


# Initialize the database when this module is imported
init()
