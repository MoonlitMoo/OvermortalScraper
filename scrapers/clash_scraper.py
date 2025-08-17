import time
from typing import List

import joblib

from core.screen import Screen
from core.screenshot_processor import ScreenshotProcessor, parse_text_number
from db.service.char_scraper_service import CharacterScraperService
from scrapers.character_scraper import CharacterScraper


class ClashScraper:

    def __init__(self, screen: Screen, session, processor: ScreenshotProcessor, logger):
        self.logger = logger
        self.screen = screen
        # self.service = ClashScraperService(session)
        self.processor = processor
        self.taoist_scraper = CharacterScraper(
            screen=screen, service=CharacterScraperService(session), processor=processor, logger=logger)

        # Set custom params
        self.screen.green_select = (300, 450, 700, 900)
        self.screen.filter_notifications = True
        self.own_br = None
        self.simple_model = joblib.load("total_br_model.joblib")

    def get_opponent_brs(self):
        """ Gets the opponent BRs in Seek Opponent screen.
        Also sets own br.

        Returns
        -------
        brs : list of float
            Opponent brs sorted from the highest challenge rank to lowest
        """
        # Scroll down to get all opponents in frame
        self.screen.swipe_down(100, 100)
        time.sleep(.1)  # Wait for settle
        matches = self.screen.find_all_images("resources/clash_scraper/seek_br_symbol.png")
        matches = sorted(matches, key=lambda i: i[0][1])  # Sort in descending order (highest -> lowest challenge)
        brs = []
        img = self.screen.colour()
        for (x, y), _ in matches:
            # Predefined area for BR value, just need y vals to get height correct
            text = self.processor.extract_text_from_area(img, (285, 450, y, y + 40))
            brs.append(parse_text_number(text))

        # Split last one (own br)
        self.logger.debug(f"Found opponent brs {brs[:-1]} with own br {brs[-1]}")
        self.own_br = brs[-1]
        return brs[:-1]


    def basic_predict(self, enemy_brs: List[float]):
        """ Predict win probability for own taoist vs opponents."""
        proba = []
        for br in enemy_brs:
            diff = self.own_br - br
            p = self.simple_model.predict_proba([[self.own_br, br, diff]])
            proba.append(p[0][1])  # Returned as (lose, win)

        self.logger.debug(f"Found probabilities {proba}")
        return proba
    def run(self, attempts: int = 3):
        # For each attempt
        # Get opponent brs
        # Run first stage prediction
        # For close, get second stage prediction
        # Choose the best candidate or refresh if no good.
        # Challenge + record result.
        pass
