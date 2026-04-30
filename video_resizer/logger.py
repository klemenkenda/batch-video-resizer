import logging
import os
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

    # Use a user-writable default location to avoid Program Files permission errors.
    if os.path.basename(log_file) == log_file:
        base_dir = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        app_log_dir = os.path.join(base_dir, "VideoResizerStudio", "logs")
        os.makedirs(app_log_dir, exist_ok=True)
        resolved_log_file = os.path.join(app_log_dir, log_file)
    else:
        resolved_log_file = log_file

    try:
        file_handler = logging.FileHandler(resolved_log_file, encoding="utf-8")
    except OSError:
        # Last-resort fallback if custom path is not writable.
        fallback_dir = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "VideoResizerStudio", "logs")
        os.makedirs(fallback_dir, exist_ok=True)
        fallback_file = os.path.join(fallback_dir, "video_resizer.log")
        file_handler = logging.FileHandler(fallback_file, encoding="utf-8")

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )

    logger.addHandler(file_handler)
    return logger
