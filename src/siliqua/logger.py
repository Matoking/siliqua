import logging


__all__ = (
    "logger", "set_verbosity_level"
)

logging.basicConfig(
    stream=None, level=logging.CRITICAL,
    format="%(asctime)s - %(name)s (%(levelname)s): %(message)s"
)
logger = logging.getLogger("siliqua")


def set_verbosity_level(verbosity_level=0):
    """
    Set the logging verbosity level

    :param verbosity_level: Verbosity level as defined in `logging` module
    """
    if verbosity_level == 0:
        logger.setLevel(logging.ERROR)
    elif verbosity_level == 1:
        logger.setLevel(logging.WARNING)
    elif verbosity_level == 2:
        logger.setLevel(logging.INFO)
    elif verbosity_level >= 3:
        logger.setLevel(logging.DEBUG)
