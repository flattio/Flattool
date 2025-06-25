import sqlite3
import json
import logging

# Set up a logger for the database module
logger = logging.getLogger(__name__)

DATABASE_FILE = "data/flatool.db"


def init():
    """
    Initializes the SQLite database and creates all necessary tables if they don't exist.
    This includes tables for config, counting, reputation, staff_roles, and takerep_blacklist.
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
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reputation (
            user_id INTEGER PRIMARY KEY,
            rep INTEGER DEFAULT 0
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS staff_roles (
            role_id INTEGER PRIMARY KEY
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS takerep_blacklist (
            user_id INTEGER PRIMARY KEY
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


def update_reputation(user_id: int, amount: int):
    """
    Updates the reputation of a user by adding 'amount' to their current reputation.
    If the user does not exist in the table, insert them with the given amount.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reputation (user_id, rep)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET rep = rep + excluded.rep
            """,
            (user_id, amount),
        )
        conn.commit()
        logger.info(f"Updated reputation for user_id={user_id} by {amount}.")
    except sqlite3.Error as e:
        logger.error(f"Error updating reputation: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def get_reputation(user_id: int) -> int:
    """
    Retrieves the reputation value for a given user_id.
    Returns the reputation as an integer, or 0 if the user is not found.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT rep FROM reputation WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error as e:
        logger.error(f"Error retrieving reputation: {e}", exc_info=True)
        return 0
    finally:
        if conn:
            conn.close()


def clear_reputation():
    """
    Deletes all rows from the reputation table, clearing all user reputations.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reputation")
        conn.commit()
        logger.info("All reputations cleared from the database.")
    except sqlite3.Error as e:
        logger.error(f"Error clearing reputation table: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def get_rank(user_id: int) -> int:
    """
    Returns the 1-based rank of the user by reputation.
    If the user is not found, returns None.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT rank FROM (
                SELECT user_id, RANK() OVER (ORDER BY rep DESC) as rank
                FROM reputation
            ) WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except sqlite3.Error as e:
        logger.error(f"Error retrieving user rank: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()


def get_leaderboard() -> list:
    """
    Retrieves all users and their reputation counts, ordered from most to least reputation.
    Returns a list of tuples: (user_id, rep).
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, rep FROM reputation ORDER BY rep DESC")
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        logger.error(f"Error retrieving leaderboard: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()


def add_staff(role_id: int):
    """
    Adds a role ID to the staff_roles table.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO staff_roles (role_id) VALUES (?)",
            (role_id,),
        )
        conn.commit()
        logger.info(f"Added role_id={role_id} to staff_roles.")
    except sqlite3.Error as e:
        logger.error(f"Error adding staff role: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def remove_staff(role_id: int):
    """
    Removes a role ID from the staff_roles table.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM staff_roles WHERE role_id = ?",
            (role_id,),
        )
        conn.commit()
        logger.info(f"Removed role_id={role_id} from staff_roles.")
    except sqlite3.Error as e:
        logger.error(f"Error removing staff role: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def is_staff(role_id: int) -> bool:
    """
    Checks if the given role_id exists in the staff_roles table.
    Returns True if the role_id is present, False otherwise.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM staff_roles WHERE role_id = ? LIMIT 1",
            (role_id,),
        )
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        logger.error(f"Error checking staff role: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()


def get_staff() -> list:
    """
    Retrieves all role_ids from the staff_roles table.
    Returns a list of role_ids.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT role_id FROM staff_roles")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error retrieving staff roles: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()


def add_to_takerep_blacklist(user_id: int):
    """
    Adds a user_id to the takerep_blacklist table.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO takerep_blacklist (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()
        logger.info(f"Added user_id={user_id} to takerep_blacklist.")
    except sqlite3.Error as e:
        logger.error(f"Error adding to takerep_blacklist: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def remove_from_takerep_blacklist(user_id: int):
    """
    Removes a user_id from the takerep_blacklist table.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM takerep_blacklist WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        logger.info(f"Removed user_id={user_id} from takerep_blacklist.")
    except sqlite3.Error as e:
        logger.error(f"Error removing from takerep_blacklist: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()


def is_in_takerep_blacklist(user_id: int) -> bool:
    """
    Checks if the given user_id exists in the takerep_blacklist table.
    Returns True if present, False otherwise.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM takerep_blacklist WHERE user_id = ? LIMIT 1",
            (user_id,),
        )
        result = cursor.fetchone()
        return result is not None
    except sqlite3.Error as e:
        logger.error(f"Error checking takerep_blacklist: {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()


def get_takerep_blacklist() -> list:
    """
    Returns a list of all user_ids in the takerep_blacklist table.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM takerep_blacklist")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error as e:
        logger.error(f"Error retrieving takerep_blacklist: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()


# Initialize the database when this module is imported
init()
