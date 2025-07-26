import time

from scrapers.character_scraper import CharacterScraper
from core.screenshot_processor import parse_text_number, ScreenshotProcessor
from core.screen import Screen, StateNotReached
from db.service.char_scraper_service import CharacterScraperService
from db.service.ranking_scraper_service import RankingScraperService


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
    processor : ScreenshotProcessor
        OCR processor for screenshots.
    logger : Logger
        The log file to output to.
    taoist_scraper : CharacterScraper
        The scraper for characters
    current_taoist : int
        The last scraped taoist
    my_ranking : int
        Ranking of own taoist
    my_database_id : int
        Last updated database id of own taoist
    """

    def __init__(self, screen: Screen, session, processor: ScreenshotProcessor, logger):
        self.logger = logger
        self.screen = screen
        self.service = RankingScraperService(session)
        self.processor = processor
        self.taoist_scraper = CharacterScraper(
            screen=screen, service=CharacterScraperService(session), processor=processor, logger=logger)

        # Setup screen notification detection
        self.screen.green_select = (300, 900, 700, 900)
        self.current_taoist = 1
        self.my_ranking = None
        self.my_database_id = None

    def setup_self(self, allow_update: bool = True):
        """ Gets id and ranking of own taoist, updates data if required by default.

        Parameters
        ----------
        allow_update : bool
            Lets own taoist be updated if necessary in database

        Returns
        -------
        bool
            Whether self was scraped
        """

        # Get basic stats
        name = self.processor.extract_text_from_area(
            self.screen.CURRENT_SCREEN, (300, 750, 1450, 1550), use_name_reader=True)
        br_text = self.processor.extract_text_from_area(
            self.screen.CURRENT_SCREEN, (830, 1000, 1475, 1525))
        rank_text = self.processor.extract_text_from_area(
            self.screen.CURRENT_SCREEN, (55, 140, 1450, 1550))
        br_val = parse_text_number(br_text)
        rank = parse_text_number(rank_text)
        if not rank:
            self.logger.critcal("Failed to get own ranking")
            raise ValueError(f"Rank is not valid from text '{rank_text}'")
        self.my_ranking = rank

        self.my_database_id = self.service.check_for_existing_taoist(name, br_val)

        # Check exit conds
        if not allow_update:
            if self.my_database_id is None:
                self.logger.warning("Taoist ID for self was not set as allow_updates is false!")
            return False
        if self.my_database_id is not None:
            return False

        # Get stats from Compare BR screen (via Top 1)
        self.taoist_scraper.own_character = True
        self.screen.tap(550, 300)  # Top 1 pixel coords
        time.sleep(0.5)
        my_data = self.taoist_scraper.scrape()
        self.screen.back()
        time.sleep(0.5)

        # Fix name + BR, then get relics/pets from own character screen
        my_data.update({"name": name, "total_br": br_val})

        self.screen.tap(300, 1500)  # My pixel coords
        time.sleep(0.5)
        my_data.update(self.taoist_scraper.scrape_relics())
        my_data.update(self.taoist_scraper.scrape_pets())
        self.screen.back()
        time.sleep(0.5)

        self.taoist_scraper.own_character = False
        self.service.add_taoist_from_scrape(my_data)
        self.logger.debug("Updated own taoist data")
        return True

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

        # Fail if we find less than 1 rank
        # (one means that only found self, edge case when character is open while looking for ranks)
        if len(ranks) <= 1:
            self.logger.warning(f"Failed to get any ranks.")
            self.screen.capture("debug/leaderboard_read_fail.png", update=False)
            raise ValueError("No ranks found on screen")

        # Last one is always me, so we can trim it off
        return {r: y for r, y in zip(ranks[:-1], y_vals[:-1])}

    def get_taoist_pixels(self):
        """ Using the current taoist rank, get the pixel to click for thescrape. \

        Returns
        int, int | None
            Y value of the next taoist, centred in row. None if next not found.
        """
        match self.current_taoist:
            case 1:  # Get number 1 taoist
                return 550, 300
            case 2:  # Get number 2 taoist
                return 200, 300
            case 3:  # Get number 3 taoist
                return 900, 300
            case 101:  # Last taoist was 100
                return None
            case _:  # Get next numerical taoist
                pass
        assert 3 < self.current_taoist < 101, "Unknown taoist case"

        ranks = self.get_visible_ranks()

        _iter, max_iter = 0, 100
        # Continue while max and min of ranks < current rank (i.e. screen showing higher range than we want)
        while max(ranks) < self.current_taoist and min(ranks) < self.current_taoist and _iter < max_iter:
            _iter += 1
            # Assume we are above and scroll down until we find the right range.
            self.screen.swipe(1079, 1200, 1079, 1000, 200)  # 200 pixel ~1.5 rows
            self.screen.tap(1079, 1185)
            ranks = self.get_visible_ranks()

        if self.current_taoist not in ranks:
            self.logger.warning(f"Failed to get current taoist '{self.current_taoist}' after scrolling {_iter} times")
            self.screen.capture(f"debug/rank_{self.current_taoist}_missing.png", update=False)
            return None
        return 300, ranks[self.current_taoist]

    def duel_taoist(self):
        """ Duels the current taoist, then navigates back to the leaderboard.

        Returns
        -------
        did_win : bool
            If the duel was won.
        """
        # Start screen by tapping more and duel buttons
        self.screen.tap(200, 1225)
        time.sleep(0.1)
        if not self.screen.tap_button("character_screen/duel"):
            self.logger.warning("Failed to get to start duel")
            return None
        time.sleep(0.1)
        # Wait until duel is finished, with 60s timeout for long duels
        try:
            self.screen.wait_for_any_state(["battle_screen/victory", "battle_screen/defeat"], timeout=60)
        except StateNotReached:
            return None
        did_win = True if self.screen.find("state/battle_screen/victory") is not None else False
        self.logger.debug(f"Duel finished with {'win' if did_win else 'loss'}")

        # Navigate back to leaderboard by exiting end screen, swiping towards right to find leaderboard button.
        self.screen.tap(550, 1850)
        time.sleep(0.1)
        self.screen.swipe(800, 1000, 200, 1000, 200)
        self.screen.tap(1000, 800)
        # Click chaos rankings button, then top BR
        self.screen.tap_button("locations/town/chaos_rankings")
        self.screen.wait_for_state("locations/town/chaos_rankings/main_page")
        self.screen.tap(300, 500)
        self.screen.wait_for_state("locations/town/chaos_rankings/br_leaderboard")

        self.logger.debug(f"Returned to leaderboard")
        return did_win

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
        taoist_id = self.service.check_for_existing_taoist(name, br)
        do_update = True if taoist_id is None else False
        self.screen.tap(row_x, row_y)
        time.sleep(.5)
        if do_update:
            taoist_data = self.taoist_scraper.scrape()
            # Add taoist and get id in same step
            taoist_id = self.service.add_taoist_from_scrape(taoist_data).id
        self.logger.info(f"Scraped rank {self.current_taoist}.")

        # Duel and save results.
        did_win = self.duel_taoist()
        if did_win:
            self.service.add_duel_result(winner_id=self.my_database_id, loser_id=taoist_id)
        else:
            self.service.add_duel_result(winner_id=taoist_id, loser_id=self.my_database_id)

        return do_update

    def run(self, max_rank: int = 100, allow_self_update: bool = True):
        """ Iterates through leaderboard from current_taoist until max_rank.

        Parameters
        ----------
        max_rank : int
            Maximum rank to scrape to
        allow_self_update : bool
            Whether to update self.
        """
        total_read = 0
        total_added = 0

        # Set own rank + database id
        updated = self.setup_self(allow_self_update)
        if allow_self_update:
            total_read += 1
            if updated:
                total_added += 1

        # Iterate through leaderboard
        while self.current_taoist <= max_rank:
            # Skip self
            if self.current_taoist == self.my_ranking:
                self.current_taoist += 1
                continue

            # Scrape taoist
            pos = self.get_taoist_pixels()
            if self.scrape_taoist(*pos):
                total_added += 1
            total_read += 1
            self.current_taoist += 1
            time.sleep(.25)

        self.logger.info(f"Added {total_added}/{total_read} taoists from the leaderboard.")
