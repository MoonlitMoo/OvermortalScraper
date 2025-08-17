import time
from typing import List

import joblib

from core.screen import Screen
from core.screenshot_processor import ScreenshotProcessor, parse_text_number
from db.service.char_scraper_service import CharacterScraperService
from db.service.ranking_scraper_service import RankingScraperService
from scrapers.character_scraper import CharacterScraper


class ClashScraper:

    def __init__(self, screen: Screen, session, processor: ScreenshotProcessor, logger):
        self.logger = logger
        self.screen = screen
        self.service = RankingScraperService(session)
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

    def get_opponent_location(self, index: int):
        """ Get the screen location of the enemy taoist at given index in list.

        Parameters
        ----------
        index : int
            The index of the taoist to return the location of

        Returns
        -------
        x, y : floats
            The pixel position of the centre of the challenge button for the associated taoist.
        """
        matches = self.screen.find_all_images("resources/buttons/locations/town/clash/challenge.png")
        matches = sorted(matches, key=lambda i: i[0][1])
        if len(matches) < 5:
            self.logger.warning("Couldn't locate all possible opponents on Seek Opponent screen")
            self.screen.capture("debug/seek_opponent.png")
        # Offset y by ~ half button width = 30px
        x, y = matches[index][0]
        self.logger.debug(f"Found opponent index {index} at {x, y + 30}")
        return x, y + 30

    def basic_predict(self, enemy_brs: List[float]):
        """ Predict win probability for own taoist vs opponents.

        Parameters
        ----------
        enemy_brs : list of floats
            The enemy br to predict against our own.

        Returns
        -------
        proba : list of floats
            The win probabilities for our taoist vs each enemy.
        """
        proba = []
        for br in enemy_brs:
            diff = self.own_br - br
            p = self.simple_model.predict_proba([[self.own_br, br, diff]])
            proba.append(p[0][1])  # Returned as (lose, win)

        self.logger.debug(f"Found probabilities {proba}")
        return proba

    def get_taoist_stats(self, enemy_index):
        """ Returns the advanced taoist stats for the given index.
        Pulls the unique id from the character screen, then returns the taoist id if found in the database. Otherwise,
        scrapes new data and adds it to the database.

        Parameters
        ----------
        enemy_index : int
            The enemy to scrape

        Returns
        -------
        taoist_id : int
            The id of the enemy in the database.
        """
        pos = self.get_opponent_location(enemy_index)
        # Get taoist identifying info
        self.screen.tap(500, pos[1])
        time.sleep(1.5)
        name = self.taoist_scraper.scrape_name()['name']
        time.sleep(0.5)

        # Attempt to click the compare BR button to get BR value
        if not self.screen.tap_button("character_screen/compare_button"):
            self.logger.warning("Failed to click compare BR button to get total BR")
            br_val = 0
        else:
            time.sleep(0.5)
            br_val = self.taoist_scraper.scrape_total_br()["total_br"]

        self.screen.back()
        time.sleep(0.2)

        # Try and get database id for the taoist, otherwise scrape and add to the db.
        taoist_id = self.service.check_for_existing_taoist(name, br_val)
        if taoist_id is None:
            self.screen.tap(500, pos[1])
            time.sleep(1.0)
            taoist_data = self.taoist_scraper.scrape()
            # Add taoist and get id in same step
            taoist_id = self.service.add_taoist_from_scrape(taoist_data).id

        self.screen.back()
        time.sleep(0.2)

        return taoist_id

    def run(self, attempts: int = 3):
        # For each attempt
        # Get opponent brs
        # Run first stage prediction
        # For close, get second stage prediction
        # Choose the best candidate or refresh if no good.
        # Challenge + record result.
        pass
