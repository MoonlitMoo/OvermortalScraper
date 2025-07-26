import logging
import os
import inspect

# Define custom advanced debug level
ADVDEBUG = 5
logging.addLevelName(ADVDEBUG, "ADVDEBUG")


def advdebug(self, message, *args, **kwargs):
    if self.isEnabledFor(ADVDEBUG):
        self._log(ADVDEBUG, message, args, **kwargs)


logging.Logger.advdebug = advdebug

# Set log level from environment
LOG_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO").upper()
LOG_LEVEL_VALUE = getattr(logging, LOG_LEVEL, logging.INFO)

# Configure root logger
logging.basicConfig(
    level=LOG_LEVEL_VALUE,
    format='[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("overmortal_bot.log", mode='w')
    ]
)


# Export reusable logger
logger = logging.getLogger("OvermortalBot")
