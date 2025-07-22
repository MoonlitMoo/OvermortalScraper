import time

from log import logger
from scrapers.character_scraper import CharacterScraper
from scrapers.screenshot_processor import parse_text_number
from service.char_scraper_service import CharacterScraperService
from service.ranking_scraper_service import RankingScraperService


class RankingScraper:
    """ Scrapes taoist data from the Chaos Ranking leaderboard. """

    def __init__(self, session):
        self.service = RankingScraperService(session)
        self.taoist_scraper = CharacterScraper(CharacterScraperService(session))
        self.screen = self.taoist_scraper.screen
        self.processor = self.taoist_scraper.processor

        # Setup screen notification detection
        self.screen.green_select = (300, 900, 700, 900)
        self.current_taoist = 0
        self.my_ranking = None

    def duel_taoist(self):
        # Hit the duel button
        # Check win/loss
        pass

    def scrape_taoist_card(self, row_x, row_y):
        """ Gets taoist name and BR total from the row card. """
        if self.current_taoist <= 3:
            # Can't do it normally, so enter character and use char scraper.
            self.screen.tap(row_x, row_y)
            time.sleep(1.5)
            name = self.taoist_scraper.scrape_name()['name']
            time.sleep(.5)
            if not self.screen.tap_button("character_screen/compare_button"):
                logger.warning("[SCRAPE_TAOIST_CARD] Failed to click compare br button to get total BR")
                br_val = 0
            else:
                time.sleep(.5)
                br_val = self.taoist_scraper.scrape_total_br()["total_br"]
            self.screen.back()
            time.sleep(.2)
            self.screen.back()
            time.sleep(.2)
        else:
            # Otherwise we define boxes based on row_y and OCR the values.
            name_box = (300, 750, row_y-50, row_y)
            br_box = (830, 1000, row_y-25, row_y+25)
            self.screen.filter_notifications = True
            self.screen.update()
            name_text = self.processor.extract_text_from_area(self.screen.CURRENT_SCREEN, name_box, use_name_reader=True)
            br_text = self.processor.extract_text_from_area(self.screen.CURRENT_SCREEN, br_box)
            self.screen.filter_notifications = False
            name = name_text
            br_val = parse_text_number(br_text)
        return name, br_val

    def scrape_taoist(self, row_x, row_y):
        """ Checks current taoist and adds to database if necessary.

        Parameters
        row_x : int
            x pixel of taoist
        row_y : int
            y pixel of taoist

        Returns
        bool
            If taoist was added to database
        """
        name, br = self.scrape_taoist_card(row_x, row_y)
        # Get all records for taoists by this name, assume no duplicate names.
        records = self.service.get_taoist_records(name)
        # Then, if there are any records < 1% BR from this, we will skip as more or less the same being.
        skip = any([abs(r[2]/br - 1) < 0.01 for r in records])
        if not skip:
            self.screen.tap(row_x, row_y)
            time.sleep(.5)
            taoist_data = self.taoist_scraper.scrape()
            self.service.add_taoist_from_scrape(taoist_data)
        self.screen.back()
        logger.debug(f"[RankingScraper SCRAPE_TAOIST] Scraped rank {self.current_taoist}.")
        # TODO: Duel
        return not skip

    def get_visible_ranks(self):
        """ Gets dictionary of rank to y value from the current screen.

        Returns
        dict
            rank: y value
        """
        # Find all the BR pics, sorted in ascending y.
        br_image = "resources/ranking_scraper/br_symbol.png"
        br_positions = self.screen.find_all_images(br_image)
        br_positions = sorted(br_positions, key=lambda x: x[0][1])

        ranks = []
        y_vals = []
        self.screen.filter_notifications = True
        self.screen.update()
        self.screen.filter_notifications = False
        # Get all the ranking numbers
        for (_, y), _ in br_positions:
            box = (55, 140, y, y + 60)  # Box x + size is constant, we just need the right y values from br icons.
            text = self.processor.extract_text_from_area(self.screen.CURRENT_SCREEN, box)
            try:
                ranks.append(int(text))
                y_vals.append(y + 30)  # Set the y value to be centred on the row with +30 offset
            except ValueError:
                logger.warning(f"[get_next_taoist] Failed to get rank from text {text}.")

        # Last one is always me, so we can trim it off
        if self.my_ranking is None:
            self.my_ranking = ranks[-1]

        return {r: y for r, y in zip(ranks[:-1], y_vals[:-1])}

    def get_next_taoist(self):
        """ Using the current taoist rank, get the pixel to click for the next taoist to scrape. \

        Returns
        int, int | None
            Y value of the next taoist, centred in row. None if next not found.
        """
        match self.current_taoist:
            case 0:  # Get number 1 taoist
                return 550, 300
            case 1:  # Get number 2 taoist
                return 200, 300
            case 2:  # Get number 3 taoist
                return 900, 300
            case 100:  # Last taoist
                return None
            case _:  # Get next numerical taoist
                pass
        assert 2 < self.current_taoist < 100, "Unknown taoist case"

        next_rank = self.current_taoist + 1
        ranks = self.get_visible_ranks()
        # Try scroll if not found
        if next_rank not in ranks:
            self.screen.swipe(5, 1200, 5, 1000, 200)  # 200 pixel ~1.5 rows
            self.screen.swipe(5, 1200, 500, 1200, 100)  # Slide horizontal to stop any further scrolling
            ranks = self.get_visible_ranks()
            if next_rank not in ranks:
                logger.warning("[get_next_taoist] Failed to get next taoist after scroll")
                return None
        return 300, ranks[next_rank]

    def run(self):
        total_read = 0
        total_added = 0

        while self.current_taoist < 100:
            pos = self.get_next_taoist()
            self.current_taoist += 1
            added = self.scrape_taoist(*pos)
            time.sleep(.25)
            if added:
                total_added += 1
            total_read += 1

        logger.info(f"[RankingScraper RUN] Added {total_added}/{total_read} taoists from the leaderboard.")
