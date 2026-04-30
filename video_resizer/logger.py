import logging
import sys


def get_logger(log_file: str = "video_resizer.log", console: bool = True) -> logging.Logger:
    logger = logging.getLogger("video_resizer")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    logger.addHandler(file_handler)
    return logger
