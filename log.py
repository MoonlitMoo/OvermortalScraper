# log.py
import logging

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler("overmortal_bot.log", mode='w')  # File output
    ]
)

# Export a reusable logger
logger = logging.getLogger("OvermortalBot")
