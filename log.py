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


# Custom formatter to include class and function name
class ClassFunctionFormatter(logging.Formatter):
    def format(self, record):
        # Attempt to get class name from the call stack
        frame = inspect.currentframe()
        while frame:
            if 'self' in frame.f_locals:
                record.classname = frame.f_locals['self'].__class__.__name__
                break
            frame = frame.f_back
        else:
            record.classname = "N/A"
        return super().format(record)


formatter = ClassFunctionFormatter(
    '[%(asctime)s] [%(levelname)s] [%(classname)s.%(funcName)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Configure root logger
logging.basicConfig(
    level=LOG_LEVEL_VALUE,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("overmortal_bot.log", mode='w')
    ]
)

for handler in logging.getLogger().handlers:
    handler.setFormatter(formatter)

# Export reusable logger
logger = logging.getLogger("OvermortalBot")
