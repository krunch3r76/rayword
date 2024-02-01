# constants.py for rayword on not remote

from pathlib import Path

# paths
DATA_DIR = Path("./data")
TARGETS_FILE = DATA_DIR / "targets.txt"
WORDS_DB_FILE = DATA_DIR / "words.db"
HEAD_DEBUG_LOGFILE_NAME = "headdebug.log"
HEAD_DEBUG_LOGFILE_REMOTEPATH = Path(".") / HEAD_DEBUG_LOGFILE_NAME
TEXT_DETAILS_DB_FILE = DATA_DIR / "text_details.db"

# # other
# RAYCMD_TIMEOUT = 60.0
