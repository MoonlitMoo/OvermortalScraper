import os
import re
import time
import cv2

import numpy as np
from pytesseract import pytesseract
os.environ["BOT_LOG_LEVEL"] = "DEBUG"
from log import logger
from scrapers.screenshot_processor import ScreenshotProcesser, parse_text_number
from screen import Screen


class CharacterScraper:
    """ From the character select screen, retrieves all stats of a character found within the "Compare BR" tab. """

    def __init__(self, own_character=False):
        self.screen = Screen(logger)
        self.processer = ScreenshotProcesser()
        self._value_x_offset = 220 if own_character else 500

    def get_value(self, template_path: str):
        """ Takes an image of the description and uses the location to find the corresponding enemy value. """
        box_width = 230
        box_height = 50
        box_y_offset = -40
        # Find location
        text_area = self.screen.find_area(template_path)

        # If we haven't found it, scroll down and try again
        _iter = 0
        while text_area is None and _iter < 5:
            _iter += 1
            self.screen.swipe(820, 1200, 820, 1100)
            time.sleep(0.2)
            logger.debug(f"Scolled down to find {template_path}")
            text_area = self.screen.find_area(template_path)

        if text_area is None:
            return None

        # The search area should start at text_x + x_offset, with y being the centre of text image + y offset
        centre_y = (text_area[2] + text_area[3]) / 2
        start_y = int(centre_y + box_y_offset)
        start_x = int(text_area[0] + self._value_x_offset)
        search_area = (start_x, start_x + box_width, start_y - int(box_height / 2), start_y + int(box_height / 2))
        # Grab the value
        value = self.processer.extract_text_from_area(self.screen.colour(), area=search_area, psm=7)
        try:
            return parse_text_number(value)
        except ValueError:
            logger.debug(f"Skipped parsing {value}")
            return None

    def scrape_br_stats(self):
        ids = ['character', 'technique', 'relic', 'ability', 'curio', 'pet', 'zodiac', 'law', 'immortal', 'daemonfae',
               'field', 'samsara', 'divinity', 'miniworld']

        _iter = 0
        while not self.screen.wait_for_state("../character_scraper/br_state", timeout=2) and _iter < 5:
            _iter += 1
            self.screen.tap(800, 1800)
            time.sleep(0.5)

        if _iter >= 5:
            logger.warning(f"Failed to get to BR stats after {_iter} attempts")
            return {}

        # For each identifier (in order)
        values = {}
        for i in ids:
            val = self.get_value(f"character_scraper/br/{i}")
            if not val:
                logger.debug(f"No value for BR stat {i}")
                values[i] = 0
            else:
                values[i] = val
                logger.debug(f"Retrieved BR stat {i} = {val:.3e}")
        return values

    def scrape_stat_stats(self):
        ids = []

        _iter = 0
        while not self.screen.wait_for_state("../character_scraper/stat_state", timeout=2) and _iter < 5:
            _iter += 1
            self.screen.tap(800, 1800)
            time.sleep(0.5)

        if _iter >= 5:
            logger.warning(f"Failed to get to stats after {_iter} attempts")
            return {}

        # For each identifier (in order)
        values = {}
        for i in ids:
            val = self.get_value(f"character_scraper/stats/{i}")
            if not val:
                logger.debug(f"No value for stat {i}")
                values[i] = 0
            else:
                values[i] = val
                logger.debug(f"Retrieved stat {i} = {val:.3e}")
        return values

    def scrape(self):
        # Open screen by clicking the button
        try:
            self.screen.tap_button("../character_scraper/compare_button")
            logger.info("Opened Stats")
            # Set screen masking and filtering
            self.screen.filter_notifications = True
            self.screen.green_select = (590, 1080, 700, 900)
            # Sweep through all the compare BR value
            self.scrape_br_stats()
            logger.info("Collected BR values")
            # Sweep through all the compare STAT values
            # logger.info("Collected stat values")
            # Compile into a database.
        except Exception as e:
            self.screen.back()
            raise e
        self.screen.back()


CharacterScraper(own_character=True).scrape()
