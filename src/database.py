import sqlite3

from datetime import datetime

from . import log, add_logging_level, db_path, log_levels

add_logging_level("DB", log_levels.DB , "white")
add_logging_level("DB_OK", log_levels.DB_OK , "green")
add_logging_level("DB_ERROR", log_levels.DB_ERROR, "red")

def set_insert_query(table: str, fields: list):
    """
    `table`: str
    `fields`: list

    ### Example:
    `set_insert_query("table", ["type", "date", "chat_id", "message_id", "user_id", "text", "media_type", "media_filename"])`
    """
    return f"""
        INSERT INTO {table}
            ({", ".join(fields)})
        VALUES
            ({", ".join(["?"] * len(fields))})
    """

def create_table(table: str, fields: list):
    """
    `table`: str
    `fields`: list

    ### Example:
    `create_table("table", ["type", "date", "chat_id", "message_id", "user_id", "text", "media_type", "media_filename"])`
    """
    # check if table exists
    table_exists = False
    try:
        if read(table, ["type"]):
            table_exists = True
    except sqlite3.OperationalError:
        log.db(f"Creating table <{table}>...")
        table_exists = False

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()

        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {table}
            (date TEXT NOT NULL,
            type TEXT NOT NULL,
            {", ".join(fields)})
        """)
    
        try:
            if not table_exists and read(table, ["type"]) is not None:
                log.db_ok(f"Table <{table}> created.")
        except sqlite3.OperationalError as err:
            log.db_error(f"Table <{table}> creation failed, reason: {err}")


def write(table: str, fields: list, values: list):
    """
    `table`: str
    `fields`: list
    `values`: list

    ### Example:
    `write("table", ["type", "date", "chat_id", "message_id", "user_id", "text", "media_type", "media_filename"], [
        "new_message",
        msg.date.timestamp(),
        chat.id,
        msg.id,
        user.id if user else None,
        text,
        media_type,
        media_filename,
    ])`
    """
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()

            c.execute(set_insert_query(table, fields), values)
    except Exception as err:
        log.db_error(f"Writing from table <{table}> failed, reason: {err}")
        return None

def read(table: str, fields: list, condition=None) -> list:
    """
    `table`: str
    `fields`: list
    `condition`: str

    ### Example:
    `read("table", ["type", "date", "chat_id", "message_id", "user_id", "text", "media_type", "media_filename"], "type = 'new_message'")`
    """
    try:
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()

            if condition:
                c.execute(f"""
                    SELECT {", ".join(fields)}
                    FROM {table}
                    WHERE {condition}
                """)
            else:
                c.execute(f"""
                    SELECT {", ".join(fields)}
                    FROM {table}
                """)

            return c.fetchall()
    except Exception as err:
        log.db_error(f"Reading from table <{table}> failed, reason: {err}")
        return None

def datetime_to_db_date(date: datetime) -> str:
    """
    `date`: datetime
    """
    return date.astimezone().strftime("%Y-%m-%d %H:%M:%S.%f%z")

def db_date_to_datetime(db_date: str) -> datetime:
    """
    `db_date`: str
    """
    return datetime.strptime(db_date, "%Y-%m-%d %H:%M:%S.%f%z")