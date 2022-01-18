import logging

logger = logging.Logger(__name__)

# set logging level
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()

# add prefix
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
# log to file
handler.setFormatter(formatter)
logger.addHandler(handler)
# log to file
# logfile = logging.FileHandler('releng.log')
# logfile.setFormatter(formatter)
# logger.addHandler(logfile)
def addLogger(logger_name, logfile):
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    # set the logger name
    logger.addHandler(handler)


def info(message):
    logger.info(message)


def debug(message):
    logger.debug(message)


def warn(message):
    logger.warn(message)


def error(message):
    logger.error(message)


def critical(message):
    logger.critical(message)
