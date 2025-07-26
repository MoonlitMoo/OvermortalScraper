import time

from scrapers.character_scraper import CharacterScraper
from scrapers.screenshot_processor import parse_text_number, ScreenshotProcesser
from screen import Screen
from service.char_scraper_service import CharacterScraperService
from service.ranking_scraper_service import RankingScraperService


class RankingScraper:
    """ Scrapes taoist data from the Chaos Ranking leaderboard.

    Parameters
    ----------
    session : Session
        The database to create the services to.

    Attributes
    ----------
    screen : Screen
        The instance to interact with emulator with.
    service : CharacterScraperService
        Interact with database for this scraper specific needs.
    processor : ScreenshotProcesser
        OCR processor for screenshots.
    logger : Logger
        The log file to output to.
    taoist_scraper : CharacterScraper
        The scraper for characters
    current_taoist : int
        The last scraped taoist
    my_ranking : int
        Ranking of own taoist
    """

    def __init__(self, screen: Screen, session, processor: ScreenshotProcesser, logger):
        self.logger = logger
        self.screen = screen
        self.service = RankingScraperService(session)
        self.processor = processor
        self.taoist_scraper = CharacterScraper(
            screen=screen, service=CharacterScraperService(session), processor=processor, logger=logger)

        # Setup screen notification detection
        self.screen.green_select = (300, 900, 700, 900)
        self.current_taoist = 0
        self.my_ranking = None

    def duel_taoist(self):
        # Hit the duel button
        # Check win/loss
        pass

    def scrape_taoist_card(self, row_x, row_y, my_card: bool = False):
        """ Gets taoist name and BR total from the row card.

        Parameters
        ----------
        row_x : int
            Pixel x for card
        row_y : int
            Pixel y for card
        my_card : bool
            Whether this is the special my rank card

        Returns
        -------
        name : str
            Scraped name for the taoist
        br_val : float
            Scraped total BR for the taoist.
        """
        if self.current_taoist <= 3:
            # Top rank: open the character directly and use the character screen. Can take a while for some reason.
            self.screen.tap(row_x, row_y)
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
            self.screen.back()
            time.sleep(0.2)

        else:
            # Lower rank: use OCR to extract name and BR from the list view
            # Special card has centred name, while normal is aligned to the top
            name_box = (300, 750, row_y - 50, row_y + 50) if my_card else (300, 750, row_y - 50, row_y)
            br_box = (830, 1000, row_y - 25, row_y + 25)

            self.screen.filter_notifications = True
            self.screen.update()

            name_text = self.processor.extract_text_from_area(
                self.screen.CURRENT_SCREEN, name_box, use_name_reader=True)
            br_text = self.processor.extract_text_from_area(
                self.screen.CURRENT_SCREEN, br_box)

            self.screen.filter_notifications = False

            name = name_text
            br_val = parse_text_number(br_text)

        return name, br_val

    def requires_scrape(self, name: str, br: float):
        """ Determines if the given name, br needs to be updated or added to the database
        Checks for all taoists of the given name (probably very few duplicates of characters). Then checks to see if
        their total BR has increased by a factor of 1%, if not we don't really need to add updated entry.

        Parameters
        ----------
        name : str
            Taoist name
        br : float
            Total BR of taoist.

        Returns
        -------
        do_update : bool
            Whether taoist needs to be updated/added
        """
        # Get all records for taoists by this name, assume no duplicate names.
        records = self.service.get_taoist_records(name)
        # Then, if there are any records < 1% BR from this, we will skip as more or less the same being.
        do_update = not any([abs(r[2] / br - 1) < 0.01 for r in records])
        return do_update

    def scrape_self(self):
        """ Scrapes own taoist. Special case as required to scrape multiple areas.

        Returns
        -------
        bool
            Whether self was scraped
        """
        top1_coords = (550, 300)
        my_coords = (300, 1500)

        # Check if scrape is necessary, need to set current_taoist not in top 3 so taoist_card doesn't open character
        original_taoist = self.current_taoist
        self.current_taoist = 4
        name, br_val = self.scrape_taoist_card(*my_coords)

        if not self.requires_scrape(name, br_val):
            self.logger.debug("Did not scrape self.")
            self.current_taoist = original_taoist
            return False

        self.current_taoist = original_taoist

        # Get stats from Compare BR screen (via Top 1)
        self.taoist_scraper.own_character = True
        self.screen.tap(*top1_coords)
        time.sleep(0.5)
        my_data = self.taoist_scraper.scrape()
        self.screen.back()
        time.sleep(0.5)

        # Fix name + BR, then get relics/pets from own character screen
        my_data.update({"name": name, "total_br": br_val})

        self.screen.tap(*my_coords)
        time.sleep(0.5)
        my_data.update(self.taoist_scraper.scrape_relics())
        my_data.update(self.taoist_scraper.scrape_pets())
        self.screen.back()
        time.sleep(0.5)

        self.taoist_scraper.own_character = False
        self.service.add_taoist_from_scrape(my_data)
        self.logger.debug("Scraped self.")
        return True

    def scrape_taoist(self, row_x, row_y):
        """ Checks current taoist and adds to database if necessary.

        Parameters
        ----------
        row_x : int
            x pixel of taoist
        row_y : int
            y pixel of taoist

        Returns
        -------
        bool
            If taoist was added to database
        """
        name, br = self.scrape_taoist_card(row_x, row_y)
        do_update = self.requires_scrape(name, br)
        if self.requires_scrape(name, br):
            self.screen.tap(row_x, row_y)
            time.sleep(.5)
            taoist_data = self.taoist_scraper.scrape()
            self.service.add_taoist_from_scrape(taoist_data)
            self.screen.back()
        self.logger.info(f"Scraped rank {self.current_taoist}.")
        # TODO: Duel
        return do_update

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
                # Try to recover using last rank
                if ranks:
                    ranks.append(ranks[-1] + 1)
                    y_vals.append(y + 30)
                    self.logger.debug(f"Failed to get rank, assumed to be {ranks[-1]} due to last rank")
                else:
                    self.logger.warning(f"Failed to get rank from text '{text}'.")

        if not ranks:
            self.logger.warning(f"Failed to get any ranks.")
            self.screen.capture("debug/leaderboard_read_fail.png", update=False)
            return {}

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
                self.logger.warning(f"Failed to get next taoist '{next_rank}' after scroll")
                self.screen.capture(f"debug/rank_{next_rank}_missing.png", update=False)
                return None
        return 300, ranks[next_rank]

    def run(self, max_rank: int = 100, scrape_self: bool = True):
        """ Iterates through leaderboard from current_taoist+1 until max_rank.

        Parameters
        ----------
        max_rank : int
            Maximum rank to scrape to
        scrape_self : bool
            Whether to update self.
        """
        total_read = 0
        total_added = 0

        if scrape_self:
            added = self.scrape_self()
            if added:
                total_added += 1
            total_read += 1

        while self.current_taoist < max_rank:
            pos = self.get_next_taoist()
            self.current_taoist += 1
            if self.current_taoist == self.my_ranking:
                continue

            if self.scrape_taoist(*pos):
                total_added += 1
            total_read += 1
            time.sleep(.25)

        self.logger.info(f"Added {total_added}/{total_read} taoists from the leaderboard.")
