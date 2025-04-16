# log.py
import logging
import os

LOG_LEVEL = os.getenv("BOT_LOG_LEVEL", "INFO").upper()

# Configure root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("overmortal_bot.log", mode='w')  # File output
    ]
)

# Export a reusable logger
logger = logging.getLogger("OvermortalBot")
