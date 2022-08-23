import toml as _toml
import os as _os

from .logger import log, add_logging_level, Colorcode
from .eventSystem import subscribe, unsubscribe, post_event

class log_levels:
    """
    Log-Levels:\n
        DEBUG    = 10\n
        INFO     = 20\n
            OK        = 21\n
            DB        = 22\n
            DB_OK     = 23\n
            TG_lOGGER = 24\n
            TG_MSG    = 25\n
            TG_DEL    = 26\n
            TG_EDIT   = 27\n
        WARNING  = 30\n
        ERROR    = 40\n
            DB_ERROR = 41\n
        CRITICAL = 50\n
    """
    DEBUG = 10
    INFO = 20
    OK = 21
    DB = 22
    DB_OK = 23
    DISCORD = 24
    MSG = 25
    DELETE = 26
    EDIT = 27
    EMBED = 28
    WARNING = 30
    ERROR = 40
    DB_ERROR = 41
    CRITICAL = 50

__location__ = _os.path.realpath(_os.path.join(_os.getcwd(), _os.path.dirname(__file__))) # get current directory
project_main_directory = _os.path.dirname(__location__)

config = _toml.load(_os.path.join(project_main_directory, "config.toml"))

db_path = _os.path.join(project_main_directory, "db.sqlite3")
from .database import write as db_write, read as db_read, create_table as db_create_table, datetime_to_db_date, db_date_to_datetime