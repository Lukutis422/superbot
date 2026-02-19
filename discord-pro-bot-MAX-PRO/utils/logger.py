import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(*, log_level: str = "INFO", log_file: str = "logs/bot.log") -> logging.Logger:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger("probot")
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    logger.propagate = False

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, log_level, logging.INFO))
    ch.setFormatter(fmt)

    fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setLevel(getattr(logging, log_level, logging.INFO))
    fh.setFormatter(fmt)

    logger.handlers.clear()
    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger
