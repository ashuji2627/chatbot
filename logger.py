import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "chatbot.log")


os.makedirs(LOG_DIR, exist_ok=True)


class SessionFormatter(logging.Formatter):
    def format(self, record):
        record.session_id = getattr(record, "session_id", "global")
        return super().format(record)

formatter = SessionFormatter(
    "%(asctime)s — [%(session_id)s] — %(levelname)s — %(message)s"
)

logger = logging.getLogger("chatbot_logger")
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5)
file_handler.setFormatter(formatter)


if not logger.handlers:
    logger.addHandler(file_handler)


class SessionLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return msg, {"extra": {"session_id": self.extra.get("session_id", "global")}}

def get_logger(session_id=None):
    return SessionLoggerAdapter(logger, {"session_id": session_id or "global"})
