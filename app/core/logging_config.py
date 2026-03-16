import logging
import sys


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        # Assume logging is already configured by the host environment.
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
